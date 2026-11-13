# MODIS–VIIRS Column Mismatch Analysis

## Dataset overview

| Parameter | MODIS | VIIRS |
|---|---:|---:|
| Dataset | MODIS_SP | VIIRS_SNPP_SP |
| Rows downloaded | 5,290 | 16,476 |
| Instrument | MODIS | VIIRS |
| Satellite | Aqua and Terra | Suomi-NPP |
| Nominal pixel size | 1 km | 375 m |

## Column differences

| Topic | MODIS | VIIRS | Required handling |
|---|---|---|---|
| Brightness | brightness | bright_ti4 | Preserve separately |
| Secondary brightness | bright_t31 | bright_ti5 | Preserve separately |
| Confidence | Numeric 0–100 | l/n/h | Keep numeric and categorical values separately |
| FRP | Per MODIS pixel | Per VIIRS pixel | Investigate resolution and calibration differences |
| Scan | 1.0–4.8 km | 0.32–0.80 km | Preserve footprint information |
| Track | 1.0–2.0 km | 0.36–0.78 km | Preserve footprint information |
| Satellite | Aqua/Terra | N (Suomi-NPP) | Filter MODIS to Aqua |

## Important observations

1. MODIS contains 5,202 Aqua and 88 Terra observations.
2. VIIRS contains 16,476 Suomi-NPP observations.
3. VIIRS has approximately 3.11 times as many detections in the downloaded files.
4. MODIS median FRP is 9.6 MW; VIIRS median FRP is 3.7 MW.
5. MODIS confidence is numerical, while VIIRS confidence is categorical.
6. MODIS and VIIRS have different nominal spatial resolutions.

## Cleaning decisions

- Retain Aqua MODIS for primary matching.
- Retain Suomi-NPP VIIRS.
- Standardize acquisition timestamps.
- Remove duplicate observations.
- Preserve sensor-specific confidence information.
- Preserve FRP and scan/track measurements.
- Do not directly equate confidence classes or FRP measurements without calibration.

## Limitations

The downloaded observation counts alone do not establish detection sensitivity. Swath overlap, acquisition time, spatial resolution and observation conditions must be considered before calculating detection differences.
