# Model Comparison Report (unseen test set)

- **Unseen test recordings:** 336 (MEETS the 100 minimum)
- **Python accuracy on this report:** 0.8542
- **Second Python model accuracy:** 0.7976
- **GTM comparison:** BLOCKED — GTM model unavailable

## Per-class test coverage (SRS wants >=10 each)

| Class | Test recordings | >=10? |
|---|---:|:--:|
| machinery_fault | 30 | yes |
| glass_breaking | 51 | yes |
| alarm_siren | 18 | yes |
| vehicle_horn | 6 | NO |
| animal_sound | 72 | yes |
| gunshot | 18 | yes |
| panic_scream | 18 | yes |
| person_asking_for_help | 45 | yes |
| aggression | 36 | yes |
| background_noise | 42 | yes |

### REQUIRED DATA NOT AVAILABLE
These classes have <10 unseen test recordings: {'vehicle_horn': 6}. Import more real recordings and re-run the pipeline to satisfy the >=10-per-class requirement.

### GTM columns
GTM is not configured, so `gtm_pred`/`gtm_conf` are `NOT AVAILABLE` and the Python vs GTM comparison is BLOCKED. A second independent Python model is included (`second_model_*`) as an interim cross-model comparison. Configure a real GTM export (see documentation/GOOGLE_TEACHABLE_MACHINE.md) to complete this.