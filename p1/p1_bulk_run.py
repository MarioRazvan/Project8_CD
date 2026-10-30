#!/usr/bin/env python3
"""P8 / P1: demonstratie bulk TCP iperf3 din ambele site-uri catre dca.

De rulat din CLI Mininet, cu obiectul net deja pornit:
px exec(open('/home/mario/project8/p1/p1_bulk_run.py').read(), {'net': net})

Creeaza servere iperf3 separate, pe porturi distincte, pentru a permite
clienti simultani din mai multe hosturi (iperf3 permite un client per server).
"""
import json
import os
import subprocess
import time

DEST_IP = '10.0.0.241'
DURATION = 10  # doar demonstratie P1; experimentele finale cer 120 secunde
PROJECT = '/home/mario/project8/p1'
OUTDIR = os.path.join(PROJECT, 'logs', 'bulk')
SCENARIOS = [
    ('0', []),
    ('2', ['h1', 'h21']),
    ('5', ['h1', 'h2', 'h3', 'h21', 'h22']),
]


def main(net):
    os.makedirs(OUTDIR, exist_ok=True)
    for name in ('dca', 'h1', 'h21'):
        location = net.get(name)
        if not location.cmd('command -v iperf3').strip():
            print('EROARE: iperf3 nu este instalat (verificat pe %s).' % name)
            print('Intr-un terminal Ubuntu normal: sudo apt install iperf3')
            return

    dca = net.get('dca')
    report = [
        'P8 / P1 - BULK TCP iperf3',
        'Destinatie: dca (%s)' % DEST_IP,
        'Durata demo: %d secunde / scenariu activ' % DURATION,
        'Scenarii: 0, 2, 5 fluxuri TCP simultane',
    ]
    for scenario, host_names in SCENARIOS:
        report.append('')
        report.append('=== BULK = %s FLUXURI ===' % scenario)
        if not host_names:
            report.append('Niciun client iperf3 pornit (scenariul de baza).')
            continue
        servers = []
        clients = []
        handles = []
        try:
            # Un server/port pentru fiecare client: iperf3 nu accepta in mod
            # general mai multi clienti simultani pe acelasi proces-server.
            for index, host_name in enumerate(host_names):
                port = 5201 + index
                server_path = os.path.join(OUTDIR, 'bulk_%s_server_%d.log' % (scenario, port))
                f = open(server_path, 'w')
                handles.append(f)
                proc = dca.popen(['iperf3', '-s', '-1', '-p', str(port)],
                                 stdout=f, stderr=subprocess.STDOUT)
                servers.append(proc)
            time.sleep(1)
            for index, host_name in enumerate(host_names):
                port = 5201 + index
                output_path = os.path.join(OUTDIR, 'bulk_%s_%s.json' % (scenario, host_name))
                f = open(output_path, 'w')
                handles.append(f)
                proc = net.get(host_name).popen(
                    ['iperf3', '-c', DEST_IP, '-p', str(port), '-t', str(DURATION), '-J'],
                    stdout=f, stderr=subprocess.STDOUT)
                clients.append((host_name, proc, output_path))
            for _, proc, _ in clients:
                try:
                    proc.wait(timeout=DURATION + 35)
                except subprocess.TimeoutExpired:
                    proc.terminate()
                    proc.wait(timeout=5)
            for handle in handles:
                handle.flush()
            successes = 0
            total_mbps = 0.0
            for host_name, proc, output_path in clients:
                try:
                    with open(output_path, 'r') as f:
                        data = json.load(f)
                    if proc.returncode != 0 or data.get('error'):
                        raise RuntimeError(data.get('error', 'client iperf3 exit=%s' % proc.returncode))
                    end = data.get('end', {})
                    summary = end.get('sum_received') or end.get('sum_sent') or {}
                    mbps = float(summary['bits_per_second']) / 1e6
                    successes += 1
                    total_mbps += mbps
                    report.append('%s -> dca | TCP port %d | OK | %.2f Mbit/s' % (
                        host_name, 5201 + host_names.index(host_name), mbps))
                except (OSError, ValueError, KeyError, TypeError, RuntimeError) as exc:
                    report.append('%s -> dca | EROARE: %s | vezi %s' % (
                        host_name, exc, output_path))
            report.append('Fluxuri reusite: %d/%d' % (successes, len(host_names)))
            report.append('Throughput agregat aproximativ: %.2f Mbit/s' % total_mbps)
        finally:
            for proc in servers:
                if proc.poll() is None:
                    proc.terminate()
            for proc in servers:
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait()
            for handle in handles:
                handle.close()

    path = os.path.join(OUTDIR, 'p1_bulk_summary.txt')
    with open(path, 'w') as f:
        f.write('\n'.join(report) + '\n')
    print('\n'.join(report))
    print('\nRaport salvat in:', path)


main(net)
