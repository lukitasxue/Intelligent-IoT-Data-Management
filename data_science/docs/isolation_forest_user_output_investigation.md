# Isolation Forest User Output Investigation

## 1. Purpose

The current Isolation Forest implementation is successfully detecting anomalies and
producing `POINTWISE_ANOMALY` results through the existing Models pipeline.

The purpose of this investigation is not to replace Isolation Forest or to tune the
model simply to reduce the number of alerts.

The purpose is to investigate how the existing Isolation Forest results can be
presented in a way that is useful and understandable to a non-technical product user.

The investigation focuses on:

- the current number of detected anomalies
- the default contamination configuration
- anomaly scores
- repeated and consecutive anomalies
- temporal grouping
- sensor-value context
- high-volume anomaly cases
- zero-anomaly cases
- possible severity information
- possible user-facing summaries
- possible aggregation approaches

The objective is to identify which information provides genuine value to the user
rather than assuming that every possible output improvement is useful.

---

# 2. Current Isolation Forest Behaviour

The current Isolation Forest detector produces pointwise anomaly results.

The detector currently uses the following default configuration:

- `contamination=0.05`
- `n_estimators=100`
- `random_state=42`

The detector produces information including:

- anomaly flag
- anomaly score
- timestamp
- model name
- runtime
- metrics associated with the input data

The existing integrated Models pipeline converts detected anomalies into
`POINTWISE_ANOMALY` results.

The current output therefore provides technically useful anomaly information.
However, individual pointwise anomaly results do not necessarily provide enough
context for a non-technical user to understand the overall situation.

---

# 3. Baseline Dataset and Investigation

The user-output investigation used:

`data_science/datasets/complex.csv`

The dataset contains:

- 1,008 readings
- three sensor metrics: `s1`, `s2`, and `s3`

The `time` column was treated as the timestamp and was not used as a sensor feature
in the user-output experiments.

For the user-output investigation, Isolation Forest was run directly on the three
sensor metrics using:

```text
contamination=0.05
random_state=42
```

The result was:

- Total readings: **1,008**
- Anomalous readings: **51**
- Anomaly rate: **5.06%**

## Separate detector evaluation

The executable `data_science/detectors/iforest_detector.py` performs a separate
evaluation experiment in which anomalies are injected into the data before the
model is evaluated.

That experiment reported:

- Injected/actual anomalies: **76**
- Flagged readings: **51**
- True positives: **51**
- False positives: **0**
- False negatives: **25**
- Accuracy: **97.52%**
- Anomaly precision: **1.00**
- Anomaly recall: **0.67**
- Anomaly F1-score: **0.80**
- Runtime: approximately **0.0152 seconds**

These evaluation metrics are useful for technical model evaluation. They are not
considered the primary information that should be presented to a non-technical
product user.

The injected-anomaly evaluation and the direct user-output investigation are kept
separate because they answer different questions.

---

# 4. Investigation of Contamination and Alert Volume

The effect of the contamination parameter was tested using the same
`complex.csv` dataset and the same three sensor metrics.

| Contamination | Flagged readings | Percentage of readings |
|---:|---:|---:|
| 0.01 | 11 | 1.09% |
| 0.05 | 51 | 5.06% |
| 0.10 | 101 | 10.02% |
| 0.20 | 202 | 20.04% |

## Finding

The number of flagged readings changes substantially with the configured
contamination value.

For the tested dataset, increasing contamination from `0.01` to `0.20` changed the
number of flagged readings from 11 to 202.

This demonstrates that the raw anomaly count is strongly influenced by the detector
configuration.

## Implication for user output

A user-facing message should therefore provide context around the anomaly count
rather than presenting the count by itself.

For example:

> 51 anomalous readings out of 1,008 readings (5.06%).

is more informative than:

> 51 anomalies detected.

The investigation does not recommend changing contamination simply to reduce the
number of user-visible alerts. Changing contamination changes detector behaviour
rather than addressing how detected results are communicated.

---

# 5. Investigation of Repeated and Consecutive Anomalies

With `contamination=0.05`, the 51 detected anomalous readings were grouped using
strict consecutive timestamps.

The results were:

| Group | Time range | Anomalous readings |
|---:|---:|---:|
| 1 | 300–305 | 6 |
| 2 | 387–398 | 12 |
| 3 | 403–403 | 1 |
| 4 | 544–546 | 3 |
| 5 | 551–571 | 21 |
| 6 | 593–599 | 7 |
| 7 | 1007–1007 | 1 |
| **Total** | | **51** |

Therefore:

- Pointwise anomaly readings: **51**
- Temporal anomaly groups: **7**

The largest group contains 21 consecutive anomalous readings from time 551 to 571.

## Finding

The pointwise output can contain multiple anomaly records that belong to the same
continuous period of unusual behaviour.

For example, the 21 anomalous readings from time 551 to 571 can be represented as
one event containing 21 anomalous readings rather than 21 separate user-facing
events.

## Implication

Grouping consecutive anomaly readings into time-based events is a strong candidate
for improving the readability of the output.

The current investigation uses strict consecutive timestamps.

It does not establish that anomalies separated by one or more normal readings should
automatically belong to the same event.

A gap-tolerant grouping rule would require additional investigation before being
implemented.

---

# 6. Investigation of High Anomaly Volume

A higher contamination value was used to investigate a scenario with many anomaly
readings.

Using:

```text
contamination=0.20
```

the detector produced:

- **202 anomalous readings**
- **18 temporal anomaly groups**

Some of the largest groups were:

| Time range | Anomalous readings |
|---:|---:|
| 379–425 | 47 |
| 511–582 | 72 |
| 585–605 | 21 |
| 607–622 | 16 |
| 949–958 | 10 |
| 999–1007 | 9 |

## Finding

A high number of pointwise anomaly records can represent a much smaller number of
continuous anomaly periods.

For example, 202 anomalous readings were represented by 18 temporal groups under
the strict consecutive-timestamp grouping rule.

One group contained 72 consecutive anomalous readings.

## Implication

Presenting every pointwise anomaly as an independent user-facing result can become
difficult to interpret when anomaly volume is high.

Event-level aggregation can provide a more compact representation while preserving
the underlying pointwise results for technical analysis.

---

# 7. Investigation of Anomaly Scores

The anomaly scores of the detected readings were examined by temporal anomaly group.

For `contamination=0.05`:

| Group | Time range | Mean score | Maximum score | Count |
|---:|---:|---:|---:|---:|
| 1 | 300–305 | 0.010267 | 0.019480 | 6 |
| 2 | 387–398 | 0.009341 | 0.014847 | 12 |
| 3 | 403–403 | 0.001704 | 0.001704 | 1 |
| 4 | 544–546 | 0.002405 | 0.004300 | 3 |
| 5 | 551–571 | 0.005051 | 0.008281 | 21 |
| 6 | 593–599 | 0.001642 | 0.003158 | 7 |
| 7 | 1007–1007 | 0.005422 | 0.005422 | 1 |

The strongest individual anomaly in this run was:

- Time: **301**
- Score: **0.019480**

## Finding

The anomaly score provides information about the relative score of individual
detections, but the investigation did not establish validated score thresholds that
could be used to create meaningful universal severity categories.

The scores also vary within individual anomaly groups.

For example, the group from time 551 to 571 contains 21 anomalous readings, but its
mean score is lower than the mean score of the group from time 300 to 305.

## Decision

The investigation does **not** support introducing arbitrary:

- Low
- Medium
- High

severity categories based directly on fixed Isolation Forest score ranges.

Such thresholds would require additional domain knowledge or validation.

The raw score can remain available as technical information.

The strongest individual score may also be shown as optional secondary information,
but it should not be presented as a validated severity classification.

---

# 8. Investigation of Sensor Context

The sensor values associated with the 51 anomalous readings were compared with the
overall dataset.

## 8.1 Anomalous readings

| Sensor | Mean | Standard deviation | Minimum | Maximum |
|---|---:|---:|---:|---:|
| `s1` | 0.342 | 0.182 | 0.004 | 0.711 |
| `s2` | 1.180 | 0.798 | 0.004 | 1.957 |
| `s3` | 0.334 | 0.188 | 0.157 | 0.799 |

## 8.2 Overall dataset

| Sensor | Mean | Standard deviation | Minimum | Maximum |
|---|---:|---:|---:|---:|
| `s1` | 1.122 | 0.725 | 0.000 | 2.000 |
| `s2` | 0.940 | 0.722 | 0.000 | 2.000 |
| `s3` | 0.825 | 0.467 | 0.000 | 1.400 |

## 8.3 Sensor Scale Consideration

The current investigation also considered the effect of different sensor value
ranges because the product may receive metrics with different numerical scales.

The existing detector testing included a different-sensor-scale scenario, which
successfully executed and produced an anomaly result.

For the user-output task, the important finding is that sensor values should be
presented as contextual information rather than interpreted directly as severity.

The current investigation does not establish that a particular sensor scale causes
an anomaly or that sensor values should be compared directly across metrics without
appropriate context.

## Finding

The actual sensor values provide useful context for anomalous readings.

However, the current Isolation Forest analysis is multivariate. An anomaly may be
identified because of the combination of multiple sensor values rather than because
one particular sensor independently caused the anomaly.

## Decision

Sensor values should be retained as contextual information where useful.

The output should not automatically state that one sensor caused an anomaly unless
additional analysis supports that conclusion.

For example, the following is appropriate:

> Anomaly detected during time 551–571. Sensor values for the affected readings are
> available for investigation.

The following should not be generated solely from the current Isolation Forest
result:

> Sensor `s2` caused the anomaly.

---

# 9. Investigation of the No-Anomaly Case

A controlled dataset containing 100 identical readings was tested:

- `s1 = 1.0`
- `s2 = 2.0`
- `s3 = 0.5`

Using:

```text
contamination=0.05
random_state=42
```

the result was:

- Readings: **100**
- Anomalies: **0**

The resulting scores were effectively zero.

# 9.1 Investigation of a Low-Anomaly Case

The contamination experiment produced a lower-volume case using
`contamination=0.01`.

For the `complex.csv` dataset:

- Total readings: **1,008**
- Anomalous readings: **11**
- Anomaly rate: **1.09%**

## Finding

When relatively few anomaly readings are detected, individual anomaly information
such as timestamp, score and sensor context may remain practical to inspect directly.

This suggests that the user-facing output should support both:

- event-level summaries for repeated or high-volume anomalies
- individual anomaly details when only a small number of anomalies are detected

The investigation does not establish a fixed threshold for when the output should
switch between these views.

## Finding

A successful detection run with zero anomalies is a meaningful result.

The user should be able to distinguish a successful analysis that found no anomalies
from a failed analysis or an unavailable result.

## Implication

An explicit overall status is useful.

For example:

```text
Status: No anomalies detected
Readings analysed: 100
Anomalous readings: 0
Anomaly events: 0
```

---

# 10. Current User-Output Problems

Based on the investigation, the following problems were identified.

## 10.1 Pointwise results can represent repeated events

Multiple consecutive anomaly readings can belong to the same continuous anomaly
period.

## 10.2 Raw anomaly counts lack context

The number of flagged readings is strongly affected by the configured contamination
value.

## 10.3 Raw anomaly scores are technical information

The current investigation does not provide sufficient evidence for converting the
scores into universal user-facing severity levels.

## 10.4 Model evaluation metrics are not the same as user-facing information

Accuracy, precision, recall, F1-score and confusion matrices are useful for technical
evaluation but do not directly explain the situation to a non-technical product
user.

## 10.5 Sensor values require careful interpretation

Sensor values provide useful context, but the current multivariate detector does not
directly establish that one sensor caused an anomaly.

## 10.6 Zero anomalies should have an explicit result

An empty anomaly list does not clearly communicate whether the detector successfully
ran and found nothing.

---

# 11. Candidate Output Improvements

The following possible improvements were investigated.

## 11.1 Group consecutive anomaly readings into events

### Proposed approach

Convert consecutive anomaly points into event-level summaries.

Example:

```text
Event 1
Time range: 551–571
Anomalous readings: 21
```

instead of exposing 21 independent user-facing alerts.

### Assessment

**Supported by the investigation.**

The baseline dataset contained 51 pointwise anomalies but only 7 strict consecutive
temporal groups.

---

## 11.2 Provide an overall summary

### Proposed approach

Provide:

- overall status
- total readings analysed
- anomalous readings
- anomaly percentage
- number of anomaly events

Example:

```text
Status: Anomalies detected
Readings analysed: 1,008
Anomalous readings: 51
Anomaly rate: 5.06%
Anomaly events: 7
```

### Assessment

**Supported by the investigation.**

This provides context around the raw anomaly count.

---

## 11.3 Show anomaly event time ranges

### Proposed approach

Show the start and end time of each anomaly event.

Example:

```text
Event 1: 300–305
Event 2: 387–398
Event 3: 403
Event 4: 544–546
Event 5: 551–571
Event 6: 593–599
Event 7: 1007
```

### Assessment

**Supported by the investigation.**

The current dataset contains clear consecutive temporal groups.

---

## 11.4 Provide sensor-value context

### Proposed approach

Show relevant sensor values associated with an anomaly event.

### Assessment

**Potentially useful.**

The investigation confirms that sensor values provide additional context, but they
should not be interpreted as identifying a single causal sensor.

---

## 11.5 Show the strongest anomaly

### Proposed approach

Provide the highest-scoring detected reading or event as optional secondary
information.

### Assessment

**Potentially useful.**

The highest score identifies the highest-scoring detected reading within this
Isolation Forest run, but this does not establish that it is the most important
real-world event or that it represents a validated severity level.

---

## 11.6 Add High/Medium/Low severity

### Assessment

**Not supported by the current investigation.**

No validated score thresholds were established for converting Isolation Forest
scores into user-facing severity categories.

---

## 11.7 Show only a fixed number of anomalies

For example, showing only the top five anomaly records.

### Assessment

**Not recommended as the primary solution.**

Showing only a fixed number of anomaly records would reduce the amount of information
shown but could hide other detected anomaly periods. It also does not directly address
the repeated-alert problem identified in the temporal grouping analysis.

---

## 11.8 Change contamination to reduce the number of alerts

### Assessment

**Not recommended as the solution to the user-output problem.**

The contamination experiment demonstrated that changing the parameter changes the
number of flagged readings.

However, this changes detector behaviour rather than improving the interpretation
of detected results.

---

# 12. Recommended Solution

The investigation supports retaining the existing Isolation Forest detector and
`POINTWISE_ANOMALY` capability while adding a user-facing aggregation and summary
layer.

The proposed approach is:

```text
Existing Isolation Forest
        |
        v
Existing pointwise anomaly results
        |
        v
User-output aggregation
        |
        +---- Overall summary
        |
        +---- Temporal anomaly events
        |
        +---- Event time ranges
        |
        +---- Sensor context
        |
        +---- Optional strongest anomaly
        |
        v
User-facing result
```

The detector remains responsible for anomaly detection.

The new output layer is responsible for making the detected results easier to
understand.

---

# 13. Recommended Priorities

## Priority 1 — Aggregate consecutive anomaly readings into events

This is the primary recommendation.

Repeated consecutive anomaly readings should be represented as a time-based event
while preserving the underlying pointwise results.

Example:

```text
Event 1
Time range: 551–571
Anomalous readings: 21
```

This directly addresses the repeated-alert problem identified during testing.

---

## Priority 2 — Provide an overall anomaly summary

The output should provide:

- status
- total readings analysed
- anomalous readings
- anomaly percentage
- number of anomaly events

Example:

```text
Status: Anomalies detected

Readings analysed: 1,008
Anomalous readings: 51
Anomaly rate: 5.06%
Anomaly events: 7
```

For a successful run with no anomalies:

```text
Status: No anomalies detected

Readings analysed: 100
Anomalous readings: 0
Anomaly events: 0
```

---

## Priority 3 — Provide event time ranges

Each aggregated event should include its start and end timestamp.

This allows users to understand when unusual behaviour occurred without inspecting
individual model records.

---

## Priority 4 — Preserve relevant sensor context

Sensor values associated with the event should remain available as supporting
information.

The output should avoid automatically assigning responsibility for the anomaly to a
single sensor.

---

## Priority 5 — Retain technical details separately

The following information should remain available for technical users and detailed
investigation:

- Isolation Forest score
- model name
- runtime
- raw pointwise anomaly records
- technical evaluation metrics

These details should not be the primary information presented to a non-technical
user.

---

# 14. What Should Be Implemented Next

The next implementation should add a reusable user-output aggregation component
after the existing Isolation Forest detection stage.

The component should:

1. Receive the existing Isolation Forest pointwise results.
2. Preserve the existing `POINTWISE_ANOMALY` information.
3. Calculate the total number of readings analysed.
4. Calculate the number of anomalous readings.
5. Calculate the anomaly percentage.
6. Group consecutive anomalous timestamps into events.
7. Record the start timestamp of each event.
8. Record the end timestamp of each event.
9. Record the number of anomalous readings in each event.
10. Preserve relevant sensor context.
11. Return an explicit result when no anomalies are detected.
12. Keep the raw anomaly score available as technical information.
13. Avoid introducing unsupported score-based severity categories.

The Isolation Forest detector itself should remain unchanged for this implementation.

The change should extend the existing output flow rather than replace the current
detection model.

---

# 15. Proposed User-Facing Output

A possible user-facing result for the baseline dataset is:

```text
Anomaly Detection Summary

Status: Anomalies detected

Readings analysed: 1,008
Anomalous readings: 51
Anomaly rate: 5.06%
Anomaly events: 7

Events

1. Time range: 300–305
   Anomalous readings: 6

2. Time range: 387–398
   Anomalous readings: 12

3. Time range: 403–403
   Anomalous readings: 1

4. Time range: 544–546
   Anomalous readings: 3

5. Time range: 551–571
   Anomalous readings: 21

6. Time range: 593–599
   Anomalous readings: 7

7. Time range: 1007–1007
   Anomalous readings: 1
```

This summary does not remove the underlying pointwise results.

The pointwise results can remain available for detailed technical investigation.

---

# 16. Benefit to a Non-Technical User

The proposed output allows a non-technical user to understand the detected behaviour
without requiring knowledge of:

- Isolation Forest
- contamination
- anomaly-score calculations
- model thresholds
- confusion matrices
- other model-internal details

Instead, the user can understand:

- whether anomalies were detected
- how many readings were affected
- what percentage of readings were anomalous
- how many anomaly events occurred
- when the anomaly events occurred
- how many readings belonged to each event
- relevant sensor values when additional context is required

This changes the presentation from individual model outputs to information that is
more directly understandable to a product user.

---

# 17. Known Limitations

## 17.1 Temporal grouping rule

The current investigation uses strict consecutive timestamps.

It has not established whether a gap between anomalous readings should still be
considered part of the same event.

A gap-tolerant grouping approach would require additional investigation.

## 17.2 Severity thresholds

The investigation did not establish validated thresholds for converting
Isolation Forest scores into Low, Medium, or High severity levels.

Such thresholds should not be introduced without suitable domain knowledge or
validation.

## 17.3 Sensor attribution

The current multivariate Isolation Forest result does not directly establish that
one sensor caused an anomaly.

Sensor values should therefore be presented as context rather than causal
attribution.

## 17.4 Contamination

The number of detected anomalies depends strongly on the contamination configuration.

The proposed output improvements do not attempt to solve this model-configuration
issue.

The purpose is to make the detected results easier to understand.

---

# 18. Investigation Summary

This document records the investigation and testing performed for the Isolation Forest
user-output task.

The investigation covered:

- baseline anomaly volume
- contamination and alert volume
- repeated anomaly behaviour
- temporal grouping
- anomaly scores
- sensor-value context
- sensor scale considerations
- high-anomaly-volume behaviour
- low-anomaly-volume behaviour
- zero-anomaly behaviour
- possible severity levels
- possible user-facing aggregation

Based on the investigation, the main finding is that the existing pointwise anomaly
results can be made more useful by summarising the results at an event level while
preserving the underlying technical information.

The recommended approach is to retain the existing Isolation Forest detection
capability and add a user-facing aggregation and summary layer.

---

# 19. Final Recommendation

The investigation indicates that the main improvement should not be reducing the
number of Isolation Forest detections.

The main improvement should be improving how those detections are represented to
the user.

The proposed next step is therefore:

> **Keep the existing Isolation Forest and `POINTWISE_ANOMALY` output, and add a
> user-facing aggregation layer that summarises anomaly counts and groups
> consecutive anomaly readings into time-based events.**

This approach preserves the existing detection capability while providing a more
understandable representation of the detected behaviour.

This is the final recommendation from the investigation and testing documented in
this report.