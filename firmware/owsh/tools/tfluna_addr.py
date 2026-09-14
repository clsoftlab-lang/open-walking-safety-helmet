"""Change the I2C address of a Benewake TF-Luna (done once for the down-looking unit).

Usage (only the sensor to change connected, or at least no other device on the target address)::

    python -m owsh.tools.tfluna_addr --from 0x10 --to 0x11 [--bus 1] [--dry-run]

Register sequence (Benewake TF-Luna product manual, I2C register table; the same values are
used by budryerson/TFLuna-I2C_python):

1. write the new 7-bit address (0x08..0x77) to register 0x22 (SLAVE_ADDR)
2. write 0x01 to register 0x20 (SAVE) - settings are only persisted after this
3. write 0x02 to register 0x21 (SHUTDOWN/REBOOT) - the new address is effective after reboot

Uncertainty: the manual and community drivers agree on these registers, but firmware revisions
differ in details (e.g. whether the device ACKs the reboot write before resetting, or needs a
short delay between the writes). This tool therefore tolerates an I/O error on the reboot write,
waits, and then verifies by reading the distance registers at the new address. If verification
fails, power-cycle the sensor and run ``i2cdetect -y 1``. The TF-Luna must be in I2C mode
(connector pin 5 tied to GND) before power-up.
"""

from __future__ import annotations

import argparse
import sys
import time

REG_SAVE = 0x20
REG_REBOOT = 0x21
REG_SLAVE_ADDR = 0x22
SAVE_VALUE = 0x01
REBOOT_VALUE = 0x02


def parse_addr(text: str) -> int:
    value = int(text, 0)
    if not 0x08 <= value <= 0x77:
        raise argparse.ArgumentTypeError("address must be within 0x08..0x77")
    return value


def plan(old: int, new: int) -> list[tuple[int, int, int, str]]:
    """The writes that will be performed: (device address, register, value, description)."""
    return [
        (old, REG_SLAVE_ADDR, new, f"set SLAVE_ADDR (0x22) = 0x{new:02x}"),
        (old, REG_SAVE, SAVE_VALUE, "SAVE settings (0x20) = 0x01"),
        (old, REG_REBOOT, REBOOT_VALUE, "REBOOT (0x21) = 0x02"),
    ]


def probe(bus, addr: int) -> tuple[int, int] | None:
    try:
        d = bus.read_i2c_block_data(addr, 0x00, 6)
    except OSError:
        return None
    return d[0] | (d[1] << 8), d[2] | (d[3] << 8)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--from", dest="old", type=parse_addr, default=0x10, help="current address (default 0x10)")
    p.add_argument("--to", dest="new", type=parse_addr, required=True, help="new address, e.g. 0x11")
    p.add_argument("--bus", type=int, default=1, help="I2C bus number (default 1)")
    p.add_argument("--dry-run", action="store_true", help="print the register writes without touching the bus")
    args = p.parse_args(argv)

    if args.old == args.new:
        print("old and new address are the same; nothing to do")
        return 0
    steps = plan(args.old, args.new)
    for addr, reg, val, desc in steps:
        print(f"  dev 0x{addr:02x}: write reg 0x{reg:02x} <- 0x{val:02x}   ({desc})")
    if args.dry_run:
        return 0
    try:
        from smbus2 import SMBus  # noqa: PLC0415
    except ImportError:
        print("smbus2 is not installed: pip install smbus2 (or pip install -e .[pi])", file=sys.stderr)
        return 2

    with SMBus(args.bus) as bus:
        if probe(bus, args.old) is None:
            print(f"no TF-Luna answering at 0x{args.old:02x} on bus {args.bus}", file=sys.stderr)
            return 1
        if probe(bus, args.new) is not None:
            print(f"a device already answers at 0x{args.new:02x}; disconnect it first", file=sys.stderr)
            return 1
        for addr, reg, val, desc in steps:
            try:
                bus.write_byte_data(addr, reg, val)
            except OSError as exc:
                if reg == REG_REBOOT:
                    print(f"  (reboot write not acknowledged: {exc}; this can be normal)")
                else:
                    print(f"failed: {desc}: {exc}", file=sys.stderr)
                    return 1
            time.sleep(0.1)
        time.sleep(1.5)
        reading = probe(bus, args.new)
        if reading is None:
            print(f"verification failed: nothing at 0x{args.new:02x}. Power-cycle the sensor and check "
                  f"with 'i2cdetect -y {args.bus}'.", file=sys.stderr)
            return 1
        print(f"OK: TF-Luna now at 0x{args.new:02x} (distance {reading[0]} cm, strength {reading[1]})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
