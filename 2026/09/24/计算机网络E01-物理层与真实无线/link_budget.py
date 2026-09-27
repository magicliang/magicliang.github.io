#!/usr/bin/env python3
"""Calculate a bounded free-space link budget and Shannon upper bound."""

import argparse
import json
import math
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    x = json.loads((ROOT / "inputs.json.txt").read_text(encoding="utf-8"))
    fspl = 32.44 + 20 * math.log10(x["distance_km"]) + 20 * math.log10(x["frequency_mhz"])
    received = x["tx_power_dbm"] + x["tx_gain_dbi"] + x["rx_gain_dbi"] - x["other_loss_db"] - fspl
    noise = x["thermal_noise_density_dbm_hz"] + 10 * math.log10(x["bandwidth_hz"]) + x["noise_figure_db"]
    snr_db = received - noise
    capacity = x["bandwidth_hz"] * math.log2(1 + 10 ** (snr_db / 10))
    result = {
        "scope": "free-space and thermal-noise model; not a Wi-Fi measurement",
        "free_space_path_loss_db": round(fspl, 3),
        "received_power_dbm": round(received, 3),
        "noise_power_dbm": round(noise, 3),
        "snr_db": round(snr_db, 3),
        "shannon_upper_bound_mbps": round(capacity / 1_000_000, 3),
    }
    assert result["free_space_path_loss_db"] > 0
    assert result["shannon_upper_bound_mbps"] > 0
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
