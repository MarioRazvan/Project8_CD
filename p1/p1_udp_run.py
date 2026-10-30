#!/usr/bin/env python3
"""Run from Mininet CLI: px exec(open('/home/mario/project8/p1/p1_udp_run.py').read())

Requires a running Mininet network stored in the CLI's `net` variable.
Sends 10 packets/host at 1 Hz (20 IoT hosts -> dca, 20 -> dcb).
"""
import json
import subprocess
import time
from pathlib import Path

ROOT = Path('/home/mario/project8/p1')
UDP_SCRIPT = ROOT / 'udp_telemetry.py'
LOGS = ROOT / 'logs'
COUNT = 10
RATE_HZ = 1
PORT = 5005


def run_p1_telemetry(net):
    if not UDP_SCRIPT.is_file():
        raise FileNotFoundError(f'Missing {UDP_SCRIPT}')
    required = [f'h{i}' for i in range(1, 41)] + ['dca', 'dcb']
    missing = [n for n in required if n not in net]
    if missing:
        raise RuntimeError('Missing Mininet hosts: ' + ', '.join(missing))
    LOGS.mkdir(parents=True, exist_ok=True)
    log_a = LOGS / 'p1_udp_dca.log'
    log_b = LOGS / 'p1_udp_dcb.log'
    log_senders = LOGS / 'p1_udp_senders.log'
    python = 'python3'
    duration = COUNT / RATE_HZ + 5
    rx_procs = []
    for name, first, logfile in [('dca', 1, log_a), ('dcb', 21, log_b)]:
        argv = [python, '-u', str(UDP_SCRIPT), 'recv', '--label', name,
                '--port', str(PORT), '--first-id', str(first), '--hosts', '20',
                '--count', str(COUNT), '--duration', str(duration)]
        with open(logfile, 'w') as out:
            rx_procs.append((name, net.get(name).popen(argv, stdout=out, stderr=subprocess.STDOUT)))

    time.sleep(0.7)  # Ensure the receivers have bound their UDP sockets.
    senders = []
    with open(log_senders, 'w') as out:
        for i in range(1, 41):
            dest = '10.0.0.241' if i <= 20 else '10.0.0.242'
            argv = [python, '-u', str(UDP_SCRIPT), 'send', '--host-id', str(i),
                    '--dest', dest, '--port', str(PORT), '--count', str(COUNT),
                    '--interval', str(1 / RATE_HZ)]
            senders.append((i, net.get(f'h{i}').popen(argv, stdout=out, stderr=subprocess.STDOUT)))
    print(f'UDP telemetry running: 40 IoT hosts, 200 B/packet, {RATE_HZ} Hz, {COUNT} packets/host.')
    print('IoT Site 1 (h1..h20) -> dca (10.0.0.241); Site 2 (h21..h40) -> dcb (10.0.0.242).')
    sender_exit = [(i, proc.wait()) for i, proc in senders]
    receiver_exit = [(name, proc.wait()) for name, proc in rx_procs]
    failed_senders = [i for i, code in sender_exit if code != 0]
    results = {}
    for name, log in [('dca', log_a), ('dcb', log_b)]:
        contents = log.read_text()
        row = next((line[len('SUMMARY_JSON '):] for line in contents.splitlines()
                    if line.startswith('SUMMARY_JSON ')), None)
        if row:
            results[name] = json.loads(row)
        else:
            results[name] = None

    report_lines = [
        'P8 / P1 - UDP TELEMETRY MEASUREMENT',
        f'Configured: 40 IoT hosts | UDP payload: 200 B | Rate: {RATE_HZ} Hz/host | {COUNT} packets/host',
        'Site 1: h1-h20 -> dca (10.0.0.241); Site 2: h21-h40 -> dcb (10.0.0.242)',
        f'Senders completed successfully: {40-len(failed_senders)}/40',
    ]
    for name in ('dca', 'dcb'):
        result = results[name]
        if not result:
            report_lines.append(f'{name}: NO SUMMARY - see {LOGS}/p1_udp_{name}.log')
            continue
        report_lines.append(
            f'{name}: hosts seen {result["hosts_seen"]}/20 | '
            f'packets received {result["received_packets"]}/{result["expected_packets"]} | '
            f'packet loss {result["packet_loss_percent"]}% | '
            f'mean one-way latency {result["mean_one_way_latency_ms"]} ms | '
            f'p50 {result["p50_one_way_latency_ms"]} ms | p95 {result["p95_one_way_latency_ms"]} ms'
        )
        smp = result.get('sample')
        if smp:
            report_lines.append(f'  Example: host={smp["host"]} seq={smp["seq"]} '
                                f'bytes={smp["payload_bytes"]} timestamp_ns={smp["send_unix_ns"]} '
                                f'received_ns={smp["received_unix_ns"]} '
                                f'latency_ms={smp["latency_ms"]}')
    if failed_senders:
        report_lines.append(f'WARNING: sender failures {failed_senders} (see {log_senders})')
    for name, code in receiver_exit:
        if code:
            report_lines.append(f'WARNING: receiver {name} failed with exit status {code}')
    report_lines.append('Measurement note: sender and receiver clocks share the same emulated Linux VM clock.')
    summary_path = LOGS / 'p1_udp_summary.txt'
    summary_path.write_text('\n'.join(report_lines) + '\n')
    print('\n' + '\n'.join(report_lines))
    print(f'\nSaved: {summary_path} and per-DC logs under {LOGS}/')


run_p1_telemetry(net)
