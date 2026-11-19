"""Fixtures shaped like the fields cli_ui.format_terminal_report reads.

They were written from cli_ui.py, NOT captured from analyze_snapshot(): when you can, replace
them with real output (xflash scan --format json) so the adapter is tested on live shapes.
"""
import copy

SNAPSHOT = {'inspection': {'id': 'XPS13-2026-11-15'},
 'system': {'vendor': 'Dell Inc.',
            'model': 'XPS 13 9310',
            'os_name': 'Windows',
            'kernel_release': '10.0.22631',
            'serial_number': 'ABC123XYZ',
            'hostname': 'SELLER-PC'},
 'cpu': {'model': 'Intel Core i7-1165G7', 'cores': 4, 'threads': 8},
 'memory': {'total_gib': 15.6, 'total_bytes': 16750000000, 'speed_mts': 3200},
 'storage': {'devices': [{'model': 'Samsung PM9A1',
                          'capacity_bytes': 512110190592,
                          'protocol': 'nvme',
                          'nvme_percentage_used': 8,
                          'media_errors': 0,
                          'power_on_hours': 3412,
                          'available_spare': 100,
                          'serial': 'S6XXXX'}]},
 'battery': {'design_capacity_mwh': 60000,
             'full_charge_capacity_mwh': 43200,
             'cycle_count': 300,
             'status': 'Discharging'},
 'display': {'resolution': '1920x1200',
             'edid': {'panel_type': 'IPS',
                      'manufacturer': 'BOE',
                      'diagonal_inches': 13.4,
                      'color_depth': '10-bit'}},
 'system_extended': {'boot_firmware': 'UEFI',
                     'partition_table': 'GPT',
                     'os_pretty_name': 'Windows 11 Home',
                     'refurbish_status': 'reinstalled 14 d ago',
                     'is_recent_wipe': True},
 'thermal': {'fan_rpm': 2100, 'cpu_temp_c': 44, 'throttle_events': 0},
 'claims': {'model': 'XPS 13 9310', 'ram_gib': 32, 'storage_capacity_gb': 512, 'cpu': 'Intel Core i7-1185G7'}}

REPORT = {'risk_state': 'review',
 'finding_count': 3,
 'generated_by': 'xflash/3.1.0',
 'findings': [{'severity': 'warning',
               'rule_id': 'battery_degradation',
               'component': 'battery',
               'title': 'Battery capacity below 80 %',
               'details': 'Full charge capacity is 72.0 % of design (43,200 / 60,000 mWh).',
               'evidence': {'health_pct': 72.0, 'cycle_count': 300, 'design_mwh': 60000}},
              {'severity': 'high',
               'rule_id': 'ram_claim_shortfall',
               'component': 'memory',
               'title': 'Installed RAM below listing',
               'details': 'Listing says 32 GiB but 15.6 GiB is installed.',
               'action': 'Ask the seller for the missing module or a discount.',
               'evidence': {'observed_gib': 15.6, 'claimed_gib': 32}},
              {'severity': 'info',
               'rule_id': 'os_recent_wipe',
               'component': 'system',
               'title': 'Clean reinstall detected',
               'details': 'OS installed 14 days ago.',
               'evidence': {}}],
 'coverage': {'battery_health': 'PASSED',
              'storage_smart': 'HEALTHY',
              'memory_capacity': 'WARNING',
              'cpu_identity': 'CLEAN',
              'display_panel': 'skipped'}}


def fixture():
    return copy.deepcopy(SNAPSHOT), copy.deepcopy(REPORT)
