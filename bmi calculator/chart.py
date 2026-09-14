"""
chart.py - matplotlib BMI trend line chart (advanced tier).

The chart embeds into the tkinter window via FigureCanvasTkAgg, so it behaves
like any other widget. If matplotlib is missing the import error is caught and
the GUI falls back to a plain text history list.
"""

from datetime import datetime

# Category boundaries used to draw dashed reference lines on the chart.
GUIDE_LINES = [
    (18.5, "Underweight 18.5", "#c8860d"),
    (25.0, "Normal limit 25", "#1a7f37"),
    (30.0, "Overweight limit 30", "#c0182a"),
]

STATUS_OK = "ok"
STATUS_EMPTY = "empty"
STATUS_UNAVAILABLE = "unavailable"


def parse_timestamp(text):
    """Turn a stored ISO timestamp into a datetime, tolerating odd values."""
    try:
        return datetime.fromisoformat(text)
    except (TypeError, ValueError):
        return None


def build_figure(records, user_name, figure=None):
    """Draw the trend chart.

    Returns (status, figure, message). 'figure' is None when there is nothing
    to draw; the caller should then show 'message' instead.
    """
    try:
        from matplotlib.figure import Figure
    except ImportError:
        return STATUS_UNAVAILABLE, None, (
            "matplotlib is not installed, so the trend graph is unavailable.\n"
            "Install it with:  pip install matplotlib"
        )

    if not records:
        return STATUS_EMPTY, None, f"No records yet for '{user_name}'."

    if figure is None:
        figure = Figure(figsize=(7.2, 4.0), dpi=100)

    figure.clear()
    axes = figure.add_subplot(111)

    points = []
    for index, record in enumerate(records):
        moment = parse_timestamp(record.get("recorded_at"))
        # Fall back to the record's position when the timestamp is unreadable.
        x_value = moment if moment else index
        points.append((x_value, record["bmi"], record.get("category", "")))

    xs = [p[0] for p in points]
    ys = [p[1] for p in points]

    # Dashed guide lines for the category thresholds, but only where they fit.
    for value, label, colour in GUIDE_LINES:
        if min(ys) - 3 <= value <= max(ys) + 3:
            axes.axhline(
                value, color=colour, linestyle="--", linewidth=1, alpha=0.55
            )
            axes.annotate(
                label,
                xy=(0, value),
                xycoords=("axes fraction", "data"),
                xytext=(3, 3),
                textcoords="offset points",
                fontsize=7,
                color=colour,
            )

    axes.plot(xs, ys, marker="o", linewidth=2, color="#2f6fd0", label=user_name)

    # Label each point with its BMI so a short history is still readable.
    for x_value, y_value, _ in points:
        axes.annotate(
            f"{y_value:.1f}",
            xy=(x_value, y_value),
            xytext=(0, 7),
            textcoords="offset points",
            ha="center",
            fontsize=7,
            color="#333",
        )

    axes.set_title(f"BMI trend - {user_name}", fontsize=11, fontweight="bold")
    axes.set_ylabel("BMI")
    axes.grid(True, linestyle=":", alpha=0.45)
    axes.margins(x=0.06, y=0.18)

    # Show dates on the x axis only when the timestamps parsed successfully.
    dated = [p[0] for p in points if isinstance(p[0], datetime)]
    if len(dated) == len(points):
        axes.set_xlabel("Date")
        figure.autofmt_xdate(rotation=30, ha="right")
    else:
        axes.set_xlabel("Record number")

    if len(points) == 1:
        status = "One record so far - add another to see a trend."
    else:
        change = points[-1][1] - points[0][1]
        direction = "down" if change < 0 else ("up" if change > 0 else "unchanged")
        status = f"{len(points)} records | overall {abs(change):.2f} {direction}"
        # A single outlying timestamp (e.g. a record saved with today's date by
        # mistake) would squash every other point into a sliver at one edge.
        # Plot by position instead so the trend stays readable.
        if _dates_are_clustered(dated, len(points)) is False:
            axes.clear()
            positions = list(range(len(points)))
            for value, label, colour in GUIDE_LINES:
                if min(ys) - 3 <= value <= max(ys) + 3:
                    axes.axhline(value, color=colour, linestyle="--",
                                 linewidth=1, alpha=0.55)
            axes.plot(positions, ys, marker="o", linewidth=2,
                      color="#2f6fd0", label=user_name)
            for position, y_value in zip(positions, ys):
                axes.annotate(f"{y_value:.1f}", xy=(position, y_value), xytext=(0, 7),
                              textcoords="offset points", ha="center", fontsize=7,
                              color="#333")
            axes.set_title(f"BMI trend - {user_name}", fontsize=11, fontweight="bold")
            axes.set_ylabel("BMI")
            axes.set_xlabel("Record number")
            axes.grid(True, linestyle=":", alpha=0.45)
            # axes.clear() leaves the old date-based x limits in place, which
            # would crush the positional points into the left edge. Reset them.
            axes.set_xlim(-0.5, len(points) - 0.5)
            axes.set_xticks(positions)
            axes.set_xticklabels([str(i + 1) for i in positions])
            axes.margins(y=0.18)
            status += " (dates too uneven to plot over time)"

    figure.tight_layout()
    return STATUS_OK, figure, status
def _dates_are_clustered(dates, total):
    """True when the timestamps sit close enough together to plot over time.

    Returns None when there is nothing to judge (no dates at all). If one
    record is stamped years away from the rest, a date axis would compress the
    actual trend into a few pixels, so the caller plots by position instead.
    """
    if not dates or len(dates) < 3:
        return True

    span = max(dates) - min(dates)
    if span.days == 0:
        return True

    gaps = sorted(
        (later - earlier).days
        for earlier, later in zip(sorted(dates), sorted(dates)[1:])
    )
    # Compare the widest gap against the median gap between records.
    median_gap = gaps[len(gaps) // 2]
    if median_gap == 0:
        return True
    return gaps[-1] <= median_gap * 12
