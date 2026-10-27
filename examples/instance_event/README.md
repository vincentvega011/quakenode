# Example: replay a REAL recorded INSTANCE event (tool demonstration)

Research testbed, not an operational warning system. These configs replay one real event from the INSTANCE v3 sample
through the same streaming chain, faults, fusion and metrics as the synthetic examples. They are **tool
demonstrations**: a few events, a toy detector, no scientific claim. The repository ships configs and instructions
only; it contains no waveform data (`data/` is gitignored) and you must download the data yourself.

The development events (not part of the frozen Stage 1 draw) are listed in `docs/dev_events.txt`
(`11061071`, `11152091`, `11151081`).

## Steps

1. Get the INSTANCE v3 sample (CC BY 4.0, INGV; DOI 10.13127/instance) and extract it:

   ```bash
   mkdir -p data/raw data/instance_sample
   curl -L -o data/Instance_sample_dataset_v3.tar.bz2 https://repo.pi.ingv.it/instance/Instance_sample_dataset_v3.tar.bz2   # 1.78 GB
   tar -xjf data/Instance_sample_dataset_v3.tar.bz2 -C data/instance_sample
   ```

   (expected sha256 of the archive: `e5a2308f46149dc81e8cb1d824346cc8b7c6ef45e8dd82d15f7bbfe4955bb8dc`)

2. Install the data extra: `pip install -e ".[data,plots]"`.

3. **Release-product input** (no network needed):

   ```bash
   quakenode run examples/instance_event/config_hdf5.yaml
   ```

   Outputs and the report are labeled "INSTANCE release product, full-window processed, NOT causal input".

4. **Raw miniSEED input**: fetch the raw INGV miniSEED for the development events (sequential, about one request per
   2-4 seconds, cached in `data/raw/dev/` with the URL and sha256 of every file logged; resumable):

   ```bash
   python scripts/fetch_dev_events.py
   quakenode run examples/instance_event/config_mseed.yaml
   ```

   Stations for which INGV returns nothing are reported as excluded (reason `fetch_failed`) in `metrics.json` and the
   report. `min_stations` (default 3) must still be met.

5. Another event or the packet-loss / gap-policy sweep, with `--set` overrides:

   ```bash
   quakenode sweep examples/instance_event/sweep.yaml --set scenario.instance.event_id=11152091 --set scenario.instance.input=mseed
   ```

6. Compare the two input kinds on the same stations (event 11061071, no faults, one seed because the data are fixed):

   ```bash
   quakenode compare examples/instance_event/config_hdf5.yaml \
       --a scenario.instance.input=release_hdf5 --b scenario.instance.input=mseed \
       --set 'faults=[]' --set 'seeds=[1]'
   ```

   Both arms run on the same stations: when the miniSEED arm lacks stations (INGV returned no data), both arms are
   re-run on the common stations and the dropped stations are listed. The output directory holds `compare.md`,
   `compare.csv`, `compare.json` (with the manifest) and `plots/compare_latency.png`. Differences are B minus A.

## How the replay works

All stations of the event are placed on one clock whose zero is the earliest trace start time. A station's reference
P time is the catalog P sample (`trace_P_arrival_sample`) on that clock. Per-station detection latency is measured on
the sample clock relative to that P; event association latency is the creation time (emission clock) of the first
candidate minus the earliest catalog P time. The catalog P picks are reviewed picks with a stated uncertainty
(`trace_P_uncertainty_s`, 0.1 to 1.0 s in these events); the uncertainty is printed next to the numbers and the
reference is not "truth". The seeds only change the fault randomness: the data are fixed.
