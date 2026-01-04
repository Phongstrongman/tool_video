"""
License Generator

Script to create new license keys and add them to the database

Usage:
    python generate_license.py --days 30 --count 1
    python generate_license.py --days 365 --count 10
    python generate_license.py --list
"""
import sys
import io

# FIX ENCODING FOR WINDOWS
if sys.platform == 'win32':
    if sys.stdout and hasattr(sys.stdout, 'buffer'):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    if sys.stderr and hasattr(sys.stderr, 'buffer'):
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

import argparse
from database import Database
from datetime import datetime
from tabulate import tabulate


def generate_licenses(days: int = 30, count: int = 1, notes: str = "", tier: str = "basic"):
    """Generate one or more licenses"""
    db = Database()

    tier_names = {"basic": "Basic (100 videos)", "pro": "Pro (500 videos)", "vip": "VIP (Unlimited)"}
    tier_display = tier_names.get(tier, tier)

    print(f"\nGenerating {count} {tier.upper()} license(s) with {days} days validity...")
    print(f"Tier: {tier_display}\n")

    licenses = []
    for i in range(count):
        license_data = db.create_license(
            expiry_days=days,
            status="active",
            notes=notes,
            tier=tier
        )
        licenses.append(license_data)
        print(f"✅ Created: {license_data['license_key']} (Tier: {tier.upper()})")

    print(f"\n✅ Generated {count} license(s) successfully!\n")

    # Show summary table
    table_data = []
    for lic in licenses:
        table_data.append([
            lic['license_key'],
            lic['tier'].upper(),
            lic['monthly_limit'] if lic['monthly_limit'] > 0 else 'Unlimited',
            lic['expiry_date'],
            lic['status']
        ])

    print(tabulate(
        table_data,
        headers=['License Key', 'Tier', 'Monthly Limit', 'Expiry Date', 'Status'],
        tablefmt='grid'
    ))

    return licenses


def list_licenses(status: str = None):
    """List all licenses"""
    db = Database()

    print("\n📋 License List")
    print("=" * 100)

    licenses = db.list_licenses(status=status)

    if not licenses:
        print("No licenses found.")
        return

    table_data = []
    for lic in licenses:
        # Calculate status
        expiry = datetime.fromisoformat(lic['expiry_date'])
        days_left = (expiry - datetime.now()).days

        status_emoji = {
            'active': '✅',
            'inactive': '❌',
            'suspended': '⏸️'
        }.get(lic['status'], '❓')

        # Get tier and usage info
        tier = lic.get('tier', 'basic')
        monthly_limit = lic.get('monthly_limit', 100)
        videos_used = lic.get('videos_used', 0)
        usage_str = f"{videos_used}/{monthly_limit}" if monthly_limit > 0 else f"{videos_used}/∞"

        table_data.append([
            status_emoji,
            lic['license_key'],
            tier.upper(),
            usage_str,
            lic['expiry_date'],
            f"{days_left} days" if days_left > 0 else "Expired",
            lic['machine_id'] or 'Not bound'
        ])

    print(tabulate(
        table_data,
        headers=['', 'License Key', 'Tier', 'Usage', 'Expiry', 'Days Left', 'Machine ID'],
        tablefmt='grid'
    ))

    print(f"\nTotal: {len(licenses)} license(s)")


def update_license_status(license_key: str, status: str):
    """Update license status"""
    db = Database()

    if status not in ['active', 'inactive', 'suspended']:
        print(f"❌ Invalid status: {status}")
        print("Valid statuses: active, inactive, suspended")
        return

    success = db.update_license_status(license_key, status)

    if success:
        print(f"✅ Updated {license_key} to {status}")
    else:
        print(f"❌ License not found: {license_key}")


def extend_license(license_key: str, days: int):
    """Extend license expiry"""
    db = Database()

    success = db.extend_license(license_key, days)

    if success:
        print(f"✅ Extended {license_key} by {days} days")
        # Show updated info
        lic = db.get_license(license_key)
        if lic:
            print(f"   New expiry: {lic['expiry_date']}")
    else:
        print(f"❌ License not found: {license_key}")


def list_suspicious_licenses():
    """List licenses with suspicious activity"""
    db = Database()

    print("\n🚨 Suspicious License Activity Report")
    print("=" * 100)

    suspicious = db.get_suspicious_licenses()

    if not suspicious:
        print("\n✅ No suspicious activity detected!")
        print("\nAll licenses are behaving normally.")
        return

    print(f"\nFound {len(suspicious)} suspicious license(s):\n")

    table_data = []
    for lic in suspicious:
        # Format dates
        if lic.get('last_ip_change'):
            last_change = datetime.fromisoformat(lic['last_ip_change'])
            hours_ago = (datetime.now() - last_change).total_seconds() / 3600
            last_change_str = f"{hours_ago:.1f}h ago"
        else:
            last_change_str = "N/A"

        # Determine warning reason
        reasons = []
        if lic.get('ip_changes', 0) > 5:
            reasons.append(f"IP changed {lic['ip_changes']}x")
        if lic.get('daily_usage', 0) > 50:
            reasons.append(f"{lic['daily_usage']} videos/day")

        reason_str = ", ".join(reasons) if reasons else "Unknown"

        table_data.append([
            lic['license_key'],
            lic['tier'].upper(),
            lic.get('last_ip', 'N/A'),
            lic.get('ip_changes', 0),
            lic.get('daily_usage', 0),
            last_change_str,
            lic['status'],
            reason_str
        ])

    print(tabulate(
        table_data,
        headers=['License Key', 'Tier', 'Last IP', 'IP Changes (24h)', 'Daily Usage', 'Last Change', 'Status', 'Reason'],
        tablefmt='grid'
    ))

    print(f"\n⚠️  Detection Rules:")
    print(f"   • IP changes > 5 times in 24 hours → Suspicious")
    print(f"   • Usage > 50 videos in one day → Suspicious")
    print(f"   • Machine ID mismatch → Auto-blocked (not shown here)")

    print(f"\n📋 Actions:")
    print(f"   1. Contact the customer to verify activity")
    print(f"   2. Suspend license: python generate_license.py update <KEY> --status suspended")
    print(f"   3. Deactivate license: python generate_license.py update <KEY> --status inactive")
    print("=" * 100)


def main():
    parser = argparse.ArgumentParser(description="DouyinVoice Pro - License Generator")

    subparsers = parser.add_subparsers(dest='command', help='Commands')

    # Generate command
    gen_parser = subparsers.add_parser('generate', help='Generate new licenses')
    gen_parser.add_argument('--days', type=int, default=30, help='Validity in days (default: 30)')
    gen_parser.add_argument('--count', type=int, default=1, help='Number of licenses to generate (default: 1)')
    gen_parser.add_argument('--tier', type=str, default='basic', choices=['basic', 'pro', 'vip'], help='License tier (default: basic)')
    gen_parser.add_argument('--notes', type=str, default='', help='Optional notes')

    # List command
    list_parser = subparsers.add_parser('list', help='List all licenses')
    list_parser.add_argument('--status', type=str, choices=['active', 'inactive', 'suspended'], help='Filter by status')

    # Update command
    update_parser = subparsers.add_parser('update', help='Update license status')
    update_parser.add_argument('license_key', type=str, help='License key to update')
    update_parser.add_argument('--status', type=str, required=True, choices=['active', 'inactive', 'suspended'], help='New status')

    # Extend command
    extend_parser = subparsers.add_parser('extend', help='Extend license expiry')
    extend_parser.add_argument('license_key', type=str, help='License key to extend')
    extend_parser.add_argument('--days', type=int, required=True, help='Days to extend')

    # Suspicious command
    suspicious_parser = subparsers.add_parser('suspicious', help='Show licenses with suspicious activity')

    args = parser.parse_args()

    if args.command == 'generate':
        generate_licenses(days=args.days, count=args.count, notes=args.notes, tier=args.tier)
    elif args.command == 'list':
        list_licenses(status=args.status)
    elif args.command == 'update':
        update_license_status(args.license_key, args.status)
    elif args.command == 'extend':
        extend_license(args.license_key, args.days)
    elif args.command == 'suspicious':
        list_suspicious_licenses()
    else:
        parser.print_help()


if __name__ == "__main__":
    # If no args, show help
    import sys
    if len(sys.argv) == 1:
        print("=" * 80)
        print("DouyinVoice Pro - License Generator")
        print("=" * 80)
        print("\nQuick Examples:")
        print("  # Generate Basic tier (100 videos/month)")
        print("  python generate_license.py generate --days 30 --tier basic")
        print("\n  # Generate Pro tier (500 videos/month)")
        print("  python generate_license.py generate --days 30 --tier pro")
        print("\n  # Generate VIP tier (unlimited)")
        print("  python generate_license.py generate --days 30 --tier vip")
        print("\n  # List all licenses")
        print("  python generate_license.py list")
        print("\n  # Show suspicious licenses")
        print("  python generate_license.py suspicious")
        print("\n  # Update license status")
        print("  python generate_license.py update DVPRO-XXXX-XXXX-XXXX --status inactive")
        print("\n  # Extend license")
        print("  python generate_license.py extend DVPRO-XXXX-XXXX-XXXX --days 30")
        print("\nFor full help: python generate_license.py --help")
        print("=" * 80)
    else:
        main()
