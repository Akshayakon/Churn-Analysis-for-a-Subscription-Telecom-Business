# Build the Power BI dashboard (about 15 minutes)

`churn_dashboard.png` is the target layout. Save the finished file as `dashboard/churn_dashboard.pbix`.

## 1. Connect
**Option A (PostgreSQL):** Get Data > PostgreSQL database > server `localhost`, database `telco_churn` > select view `v_churn_dashboard` > Import.
**Option B (no database):** Get Data > Text/CSV > `dashboard/v_churn_dashboard.csv`.

In Power Query, check types: `monthly_charges`, `total_charges` = Decimal; `churn_flag`, `risk_score`, `senior_citizen` = Whole number.

## 2. Measures (Modeling > New measure)
```DAX
Customers        = COUNTROWS(v_churn_dashboard)
Churned          = SUM(v_churn_dashboard[churn_flag])
Churn Rate       = DIVIDE([Churned], [Customers])
Monthly Rev Lost = CALCULATE(SUM(v_churn_dashboard[monthly_charges]), v_churn_dashboard[churn_flag] = 1)
Annual Rev Lost  = [Monthly Rev Lost] * 12
Total MRR        = SUM(v_churn_dashboard[monthly_charges])
% MRR Lost       = DIVIDE([Monthly Rev Lost], [Total MRR])
```
Format `Churn Rate` and `% MRR Lost` as percentage, revenue measures as currency.

## 3. Visuals (one page)
| Visual | Fields |
|---|---|
| Card: churn rate | `Churn Rate` |
| Card: revenue lost | `Annual Rev Lost` |
| Clustered column: churn by contract | Axis `contract`, Values `Churn Rate` |
| Clustered column: churn by tenure | Axis `tenure_bucket`, Values `Churn Rate` |
| Column: risk band breakdown | Axis `risk_band`, Values `Churn Rate` (sort High > Medium > Low) |
| Donut: revenue by risk band | Legend `risk_band`, Values `Total MRR` |
| Bar: revenue lost by segment | Axis `contract` + `internet_service`, Values `Monthly Rev Lost` |
| Slicers | `internet_service`, `payment_method`, `gender` |

Colors: churn/high risk `#d64545`, other `#2f6fb5`, medium risk `#e8a33d`.

## 4. Check against the SQL
Cards should show 26.54% churn and $1,669,570 annual revenue lost; High Risk churn 56.90%.
