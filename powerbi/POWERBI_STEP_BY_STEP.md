# Power BI Guide: Step by Step (Beginner Friendly)

This guide shows you how to build the churn dashboard in Power BI Desktop.
You do not need to know Power BI already. It takes about 30 minutes.

**What you will build:** a one-page dashboard like `churn_dashboard.png`.
**What you need:**
- Power BI Desktop (free, from the Microsoft Store)
- The file `dashboard/v_churn_dashboard.csv` from this project

---

## Step 1. Load the data

1. Open Power BI Desktop.
2. Click **Home > Get data > Text/CSV**.
3. Pick `v_churn_dashboard.csv` and click **Open**.
4. In the preview window, click **Transform Data** (not Load).

### Check the column types
In the window that opens (Power Query), click the small icon in each column header and set:

| Column | Type |
|---|---|
| monthly_charges, total_charges | Decimal number |
| churn_flag, risk_score, senior_citizen | Whole number |
| Other columns | Text |

Then click **Close & Apply** (top left).

> **Tip:** You will see the table name `v_churn_dashboard` on the right side, in the **Data** pane. If Power BI named it differently, rename it (right-click > Rename) so the formulas below work.

---

## Step 2. Create the measures

A *measure* is a calculation, like "churn rate". You write it once and use it in many charts.

1. Click the table name in the **Data** pane.
2. Click **Table tools > New measure**.
3. Paste one formula, press **Enter**.
4. Repeat for each formula.

```DAX
Customers = COUNTROWS(v_churn_dashboard)

Churned = SUM(v_churn_dashboard[churn_flag])

Churn Rate = DIVIDE([Churned], [Customers])

Monthly Rev Lost =
CALCULATE(
    SUM(v_churn_dashboard[monthly_charges]),
    v_churn_dashboard[churn_flag] = 1
)

Annual Rev Lost = [Monthly Rev Lost] * 12

Total MRR = SUM(v_churn_dashboard[monthly_charges])

% MRR Lost = DIVIDE([Monthly Rev Lost], [Total MRR])
```

**In plain words:**
- **Customers**: how many customers there are.
- **Churned**: how many of them left.
- **Churn Rate**: churned divided by customers.
- **Monthly Rev Lost**: monthly bills of the customers who left.
- **Annual Rev Lost**: the same, times 12.
- **Total MRR**: all monthly bills (MRR means monthly recurring revenue).
- **% MRR Lost**: the share of monthly revenue that was lost.

### Set the number formats
Click a measure, then use **Measure tools** at the top:
- `Churn Rate` and `% MRR Lost`: click the **%** button.
- `Monthly Rev Lost`, `Annual Rev Lost`, `Total MRR`: click the **$** button.

---

## Step 3. Build the visuals

Click an empty spot on the canvas, then click a chart type in the **Visualizations** pane. Drag fields from the **Data** pane into the boxes. Repeat for each row below.

| # | Visual | Chart type | Where to drag the fields |
|---|---|---|---|
| 1 | Churn rate | **Card** | `Churn Rate` into *Fields* |
| 2 | Revenue lost per year | **Card** | `Annual Rev Lost` into *Fields* |
| 3 | Churn by contract | **Clustered column chart** | `contract` into *X-axis*, `Churn Rate` into *Y-axis* |
| 4 | Churn by tenure | **Clustered column chart** | `tenure_bucket` into *X-axis*, `Churn Rate` into *Y-axis* |
| 5 | Churn by risk band | **Clustered column chart** | `risk_band` into *X-axis*, `Churn Rate` into *Y-axis* |
| 6 | Revenue by risk band | **Donut chart** | `risk_band` into *Legend*, `Total MRR` into *Values* |
| 7 | Revenue lost by segment | **Clustered bar chart** | `contract` and `internet_service` into *Y-axis*, `Monthly Rev Lost` into *X-axis* |
| 8 | Filters | **Slicer** (make three) | `internet_service`, `payment_method`, `gender` |

### Sort the risk bands
For chart 5, you want High, then Medium, then Low:
1. Click the chart.
2. Click the **...** (three dots) at its top right > **Sort axis** > pick `risk_band`.
3. Click **...** again > **Sort ascending** or **Sort descending** until High Risk is first.

### Add titles
Click a chart, open the **Format** tab (paint roller icon) > **General > Title**, and type a clear title such as "Churn Rate by Contract".

---

## Step 4. Make it look good

**Layout (top to bottom):**
1. A page title at the top: **Insert > Text box**, type "Telecom Customer Churn".
2. The two cards side by side under the title.
3. The three column charts in a row below the cards.
4. The donut and the bar chart under them.
5. The three slicers down the left side or across the top.

**Colors** (Format > Visuals > Columns/Slices > Colors):

| Meaning | Color code |
|---|---|
| Churn / high risk | `#d64545` (red) |
| Normal / other | `#2f6fb5` (blue) |
| Medium risk | `#e8a33d` (orange) |

To enter a code: click the color box > **Custom color** > type the code in the **Hex** box.

**Tips:**
- Keep the same color for the same meaning across all charts.
- Turn on **Data labels** (Format > Visuals > Data labels) so people can read numbers without hovering.
- Line the visuals up with **Format > Align** so the page looks tidy.

---

## Step 5. Check your numbers

Your dashboard should match the SQL results. With no slicer selected:

| Check | Expected value |
|---|---|
| Churn Rate card | **26.54%** |
| Annual Rev Lost card | **$1,669,570** |
| High Risk churn rate (chart 5) | **56.90%** |

If a number is different:
- Look at your slicers. Make sure none are filtering the data.
- Look at the column types from Step 1.
- Look at the measure formulas for typos.

---

## Step 6. Save and share

1. **File > Save as**, and save it as `powerbi/churn_dashboard.pbix`.
2. Take a screenshot for the README: **File > Export > Export to PDF**, or use the Snipping Tool.
3. Save the image as `powerbi/churn_dashboard_powerbi.png` and add it to the README.

---

## Common problems

| Problem | Fix |
|---|---|
| A measure says the table or column can't be found | The table name must match exactly. Rename it to `v_churn_dashboard`. |
| Churn Rate shows `0.27` and not `26.54%` | Click the measure, then click the **%** button. |
| Numbers look too big | Check that `churn_flag` is a Whole number, not Text. |
| The tenure buckets are in the wrong order | They start with numbers (1, 2, 3...), so sort the axis by `tenure_bucket` ascending. |
| Charts show "(Blank)" | Check the CSV loaded fully, and that no slicer is hiding rows. |

---

## Words you may not know

- **Churn:** a customer leaves the company.
- **Measure:** a calculation you build once and reuse.
- **Slicer:** a button list that filters the whole page.
- **Card:** a box showing one big number.
- **MRR:** monthly recurring revenue, the money customers pay each month.
