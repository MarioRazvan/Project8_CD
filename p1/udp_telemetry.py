#!/usr/bin/env python3
"""P8 / P1: 200-byte UDP telemetry with timestamp and sequence number."""
import argparse
import json
import socket
import struct
import time
from collections import defaultdict


def percentile(values, q):
    if not values:
        return None
    ordered = sorted(values)
    pos = (len(ordered) - 1) * q
    lo = int(pos)
    hi = min(lo + 1, len(ordered) - 1)
    return round(ordered[lo] + (ordered[hi] - ordered[lo]) * (pos - lo), 3)

MAGIC = b'P8T1'
HEADER = struct.Struct('!4sHIQ')  # magic(4), host id(2), seq(4), Unix ns(8)
PAYLOAD_SIZE = 200


def run_sender(args):
    if args.host_id < 1 or args.host_id > 65535:
        raise ValueError('host-id must be between 1 and 65535')
    pad = b'X' * (PAYLOAD_SIZE - HEADER.size)
    addr = (args.dest, args.port)
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        deadline = time.monotonic()
        for seq in range(1, args.count + 1):
            now_ns = time.time_ns()
            data = HEADER.pack(MAGIC, args.host_id, seq, now_ns) + pad
            assert len(data) == 200
            sock.sendto(data, addr)
            print(f'SENT host=h{args.host_id} seq={seq} size={len(data)} send_unix_ns={now_ns} dest={args.dest}', flush=True)
            deadline += args.interval
            time.sleep(max(0, deadline - time.monotonic()))


def run_receiver(args):
    first_id = args.first_id
    last_id = first_id + args.hosts - 1
    seen = defaultdict(set)
    latency = []
    first_sample = None
    malformed = 0
    started = time.monotonic()
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(('0.0.0.0', args.port))
        sock.settimeout(0.5)
        print(f'RECEIVER_START site={args.label} port={args.port} expected_hosts={args.hosts} '
              f'expected_per_host={args.count} payload_bytes={PAYLOAD_SIZE}', flush=True)
        while time.monotonic() - started < args.duration:
            try:
                data, _ = sock.recvfrom(4096)
            except socket.timeout:
                continue
            if len(data) != PAYLOAD_SIZE:
                malformed += 1
                continue
            try:
                magic, host_id, seq, sent_ns = HEADER.unpack_from(data)
            except struct.error:
                malformed += 1
                continue
            if magic != MAGIC or host_id < first_id or host_id > last_id or not (1 <= seq <= args.count):
                malformed += 1
                continue
            if seq in seen[host_id]:
                continue
            received_ns = time.time_ns()
            seen[host_id].add(seq)
            latency_ms = (received_ns - sent_ns) / 1_000_000.0
            latency.append(latency_ms)
            if first_sample is None:
                first_sample = dict(host=f'h{host_id}', seq=seq, payload_bytes=len(data),
                                    send_unix_ns=sent_ns, received_unix_ns=received_ns,
                                    latency_ms=round(latency_ms, 3))
            if seq == 1 or seq == args.count:
                print(f'RECEIVED host=h{host_id} seq={seq} bytes={len(data)} '
                      f'sent_ns={sent_ns} received_ns={received_ns} latency_ms={latency_ms:.3f}', flush=True)
    expected = args.hosts * args.count
    received = sum(len(s) for s in seen.values())
    summary = dict(site=args.label, hosts_expected=args.hosts, hosts_seen=len(seen),
                   expected_packets=expected, received_packets=received,
                   lost_packets=expected-received,
                   packet_loss_percent=round(100*(expected-received)/expected, 3),
                   mean_one_way_latency_ms=round(sum(latency)/len(latency), 3) if latency else None,
                   p50_one_way_latency_ms=percentile(latency, 0.50),
                   p95_one_way_latency_ms=percentile(latency, 0.95),
                   min_one_way_latency_ms=round(min(latency), 3) if latency else None,
                   max_one_way_latency_ms=round(max(latency), 3) if latency else None,
                   malformed=malformed, sample=first_sample)
    print('SUMMARY_JSON ' + json.dumps(summary, sort_keys=True), flush=True)


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest='mode', required=True)
    s = sub.add_parser('send')
    s.add_argument('--host-id', type=int, required=True)
    s.add_argument('--dest', required=True)
    s.add_argument('--port', type=int, default=5005)
    s.add_argument('--count', type=int, default=10)
    s.add_argument('--interval', type=float, default=1.0)
    r = sub.add_parser('recv')
    r.add_argument('--label', required=True)
    r.add_argument('--port', type=int, default=5005)
    r.add_argument('--first-id', type=int, required=True)
    r.add_argument('--hosts', type=int, default=20)
    r.add_argument('--count', type=int, default=10)
    r.add_argument('--duration', type=float, default=15.0)
    args = parser.parse_args()
    if args.mode == 'send':
        run_sender(args)
    else:
        run_receiver(args)

if __name__ == '__main__':
    main()
