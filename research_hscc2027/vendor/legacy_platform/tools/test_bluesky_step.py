"""Minimal BlueSky in-process stepping smoke test (no SUMO needed)."""
import sys
from pathlib import Path

REPO = Path(r"C:\Users\user\OneDrive\桌面\学术agent\bluesky")
sys.path.insert(0, str(REPO))

import bluesky as bs

bs.init(mode="sim", detached=True, workdir=str(REPO))

# 1 s master step
bs.stack.stack("DT 1.0")
print("simdt after DT:", bs.sim.simdt)

# define two landing sites near Suzhou centre (real facility coords from config)
V2 = (31.296653, 120.595712)
V1 = (31.310801, 120.603545)

bs.stack.stack(f"DEFWPT V2,{V2[0]},{V2[1]},FIX")
bs.stack.stack(f"DEFWPT V1,{V1[0]},{V1[1]},FIX")

# create one test UAV of each type
types = ["Amzn", "M600", "Phan4", "EC35"]
for i, t in enumerate(types):
    acid = f"T{i+1}"
    bs.stack.stack(f"CRE {acid},{t},{V2[0]},{V2[1]},{90*i},100,20")

print("created:", list(bs.traf.id))
print("types  :", list(bs.traf.type))

# fly them all to V1
for acid in [f"T{i+1}" for i in range(len(types))]:
    bs.stack.stack(f"DEST {acid},V1")
    bs.stack.stack(f"ALT {acid},328")  # ~100 m

for step in range(30):
    bs.sim.step()
    if step % 5 == 0:
        t = bs.sim.simt
        ids = list(bs.traf.id)
        lats = [round(x, 5) for x in bs.traf.lat]
        lons = [round(x, 5) for x in bs.traf.lon]
        alts = [round(x, 0) for x in bs.traf.alt]
        print(f"t={t:.1f} | {list(zip(ids, lats, lons, alts))}")

print("FINAL simt:", bs.sim.simt)
bs.sim.quit()
print("DONE")
