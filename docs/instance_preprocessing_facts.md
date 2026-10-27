# What INSTANCE says about its own preprocessing

Research prototype, not an operational warning system. Retrieved 2026-10-26. This note records **quotes**, not interpretations; the interpretation column is separate and marked.

Sources read:

- Michelini et al. (2021), ESSD 13, 5509-5544, https://doi.org/10.5194/essd-13-5509-2021 (HTML at https://essd.copernicus.org/articles/13/5509/2021/ and the PDF at .../essd-13-5509-2021.pdf, text extracted with `pdftotext`). Section numbers below are the paper's.
- INGV/instance repository, https://github.com/INGV/instance, shallow clone at commit `95dc7e4933feade5e5d05482c4fbb3785ef9014a` (README, `notebooks/`, `aux/`). All files were listed; the notebooks and `.py` helpers were searched for detrend, demean, resample, taper, trim, astype, int32, dtype and linear.

Fetching worked for all of the above. Table 2 does not appear in the HTML text (it is a separate table page that returned a 404-style page), so its rows were read from the PDF.

## Quotes

**Sect. 2.1.3, Waveform data selection and download** (window and start time):

> "the time windows set for data download were defined by inserting a randomly selected buffer time ranging between 15 and 20 s before the P-wave onset arrival phase and enlarging the time window to 125 s."

> "after data processing the time windows have been all set to 120 s."

> "since the data are archived in miniSEED compressed format that features different sizes of the logical records, and since the web service extracts the full logical record containing the predefined trace start time, the start time of the trace can be earlier than the predefined minimum time of 20 s"

> "The data (miniSEED format) were downloaded using the FDSN dataselect web services provided by INGV"

**Sect. 2.1.5, Preparation of processed waveforms in digital units** (the only description of the processing steps):

> "It includes the following steps: removal of traces containing data gaps (i.e., missing data); trimming the waveform trace to the nearest sample to the start time; 120 s trace windowing; removal of mean and linear trends from the data; resampling at 100 Hz; calculation of the signal-to-noise ratio; extraction of the data quality metrics."

> "These additional parameters, providing the distribution of the trace values, have been computed using the MSEEDMetadata class of the ObsPy python software"

> "The final dataset consists of a total of 1 159 249 3C waveform data records from 54 008 earthquakes in count units assembled within an HDF5 format file."

**Sect. 2.3, Dataset description** (about the stored mean):

> "The mean values, which have been removed in the preprocessing preparation stage (cf. Sect. 2.1.5), are (obviously) centered about the zero value, whereas the median histograms, ... do display a broader distribution of values around zero. This last behavior occurs whenever the waveform trace values are unevenly distributed about the mean, and it derives from the preprocessing of faulty traces that, for example, result in defective removal of the linear trend."

**Table 2** (PDF, metadata definitions):

> `trace_start_time`: "Waveform trace UTC start time (YYYY-MM-DDTHH:MM:SS.SSZ)"
> `trace_[P,S]_arrival_time`: "P- or S-arrival UTC start time (YYYY-MM-DDTHH:MM:SS.SSZ)"
> `trace_[P,S]_arrival_sample`: "P- and S-onset sample number on waveform trace (integer)"
> `trace_eval_[P,S]`: "P- or S-type of picking (currently only “manual”)"
> `trace_[E,N,Z]_mean_counts`: "E-, N -, or Z-component sample mean (counts, integer)"
> `trace_npts`: "Number of samples in waveform trace (integer)"; `trace_dt_s`: "Sampling interval (s)"

Abstract / Sect. 1: "All the waveform traces have a length of 120 s, are sampled at 100 Hz".

**Repository.** `README.md` describes the downloads and the sample dataset; it contains no description of the processing steps. The notebooks (`Waveforms.ipynb`, `Waveforms_verify_P-onset_picking.ipynb`, `Plots.ipynb`, `Station_Hypocenter_MomentTensor.ipynb`) and `notebooks/Def_plot_waveform.py` only read and plot. `Def_plot_waveform.py` builds an ObsPy stream directly from the HDF5 array with `stats.delta = row['trace_dt_s']` and `stats.starttime = pd.to_datetime(row['trace_start_time'])`, and uses `trace_P_arrival_time` for plotting. The repository has **no code that detrends, resamples, trims or casts to integer**.

## Documented versus unknown

| item | documented? | what the sources say (quote above) / what is unknown |
|---|---|---|
| Trimming | yes | "trimming the waveform trace to the nearest sample to the start time"; the "start time" there is not defined further (predefined requested start time, per 2.1.3) |
| Window length | yes | 120 s ("120 s trace windowing"), 12,000 samples at 100 Hz |
| Mean and linear trend removal | yes, as a step name | "removal of mean and linear trends from the data" |
| Span of the detrend | **not stated** | Reading the order of the list, it comes after "120 s trace windowing", which would make it the 120 s window; that is an inference from list order, not a statement |
| Detrend method (least squares? ObsPy?) | **not stated** | ObsPy is named only for the quality metrics; no function or option is given for detrending |
| Order of mean removal, trend removal | not stated | Mathematically, a least-squares line with an intercept already removes the mean |
| Resampling | yes, as a step name | "resampling at 100 Hz"; method, and whether it was applied to traces already at 100 Hz, **not stated**. Listed after the detrend |
| Taper or filter on the counts | none described for counts | The 5% cosine taper and the 0.01/0.04/25/40 Hz corners are described only for the ground-motion product (Sect. 2.1.6) |
| Integer cast | **not stated** | The paper says the data are "in count units" and the mean-count metadata are "counts, integer"; the HDF5 arrays are `int32`. How float results of a detrend became integers is not stated |
| `trace_start_time` | partly | "Waveform trace UTC start time", written with two decimals. Not stated whether it is the exact first-sample time or a rounded one |
| `trace_P_arrival_sample` vs `trace_P_arrival_time` | partly | The sample is "P-onset sample number on waveform trace (integer)"; the relation (rounding, zero-based, rounding of the time) is **not stated** |
| P pick provenance | yes | "currently only “manual”" (matches the sample: 10,000 of 10,000) |
| Gap handling | yes | traces with data gaps were removed ("removal of traces containing data gaps") |
| Mean-counts metadata | contradiction to note | Table 2 says "counts, integer" but the sample CSV contains non-integer values (for example `trace_E_mean_counts` = -0.000333...) |

## Consequence for the detrend check

The documented steps allow a first, literal reading: window the 120 s from the sample nearest to the start time, remove mean and linear trend over that window (both together equal a least-squares line removal), then resample to 100 Hz (a no-op for traces already at 100 Hz, if it is applied as a no-op). They do not say how the result became `int32`. A transform "implemented as literally as possible" therefore equals the least-squares line removal followed by an undocumented cast, so a separate T3 would add nothing beyond the cast variants and is omitted in the pre-registration.
