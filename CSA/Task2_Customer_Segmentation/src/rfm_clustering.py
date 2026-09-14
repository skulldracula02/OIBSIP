"""
Customer Segmentation Analysis - reusable pipeline.

This module holds every step of the analysis as a function so that both the
Jupyter notebook and the command-line runner share exactly one implementation.

Pipeline:
    1. load_and_clean()      -> clean transaction-level DataFrame
    2. descriptive_stats()   -> headline business metrics
    3. build_rfm()           -> customer-level Recency/Frequency/Monetary table
    4. scale_features()      -> StandardScaler output
    5. evaluate_k()          -> Elbow (inertia) + Silhouette for k=2..10
    6. fit_kmeans()          -> fitted model + cluster labels
    7. profile_clusters()    -> mean feature values + business labels
    8. plots                 -> elbow, scatter x2, bar chart, heatmap

Run standalone:
    python src/rfm_clustering.py
"""

from __future__ import annotations

import os
import warnings

import matplotlib

matplotlib.use("Agg")  # headless-safe; notebook overrides this itself
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler

warnings.filterwarnings("ignore")

RANDOM_STATE = 42
DATA_PATH = "data/online_retail.csv"
OUT_DIR = "outputs"

sns.set_theme(style="whitegrid", palette="deep")
plt.rcParams["figure.dpi"] = 110
plt.rcParams["savefig.bbox"] = "tight"


# ---------------------------------------------------------------------------
# 1. Load + clean
# ---------------------------------------------------------------------------
def load_and_clean(path: str = DATA_PATH) -> tuple[pd.DataFrame, dict]:
    """Load raw transactions and return a clean DataFrame plus a QA report."""
    raw = pd.read_csv(path, parse_dates=["InvoiceDate"])
    report = {"raw_rows": len(raw), "raw_customers": raw["CustomerID"].nunique()}

    df = raw.copy()

    # --- a) Drop exact duplicates -----------------------------------------
    before = len(df)
    df = df.drop_duplicates()
    report["duplicate_rows_removed"] = before - len(df)

    # --- b) Normalise text: strip whitespace, fix casing ---------------
    for col in ["Country", "Description", "StockCode"]:
        if col in df.columns:
            df[col] = df[col].astype("string").str.strip()
    df["Country"] = df["Country"].str.title()

    # --- c) Missing values ------------------------------------------------
    report["missing_customerid"] = int(df["CustomerID"].isna().sum())
    report["missing_description"] = int(df["Description"].isna().sum())

    # Rows without a CustomerID cannot be assigned to any customer, so they
    # are useless for segmentation -> drop them.
    df = df.dropna(subset=["CustomerID"])
    # Description is not used in the model -> fill rather than lose the row.
    df["Description"] = df["Description"].fillna("UNKNOWN")

    # --- d) Type coercion -------------------------------------------------
    df["CustomerID"] = df["CustomerID"].astype(int)
    df["InvoiceNo"] = df["InvoiceNo"].astype("string")

    # --- e) Cancellations / returns --------------------------------------
    # Invoices starting with 'C' are credit notes (returns).
    cancel_mask = df["InvoiceNo"].str.startswith("C", na=False)
    report["cancellation_rows"] = int(cancel_mask.sum())
    df["IsCancellation"] = cancel_mask
    # Negative quantity on a non-cancellation invoice is also a return.
    df["IsReturn"] = cancel_mask | (df["Quantity"] < 0)
    report["negative_quantity_rows"] = int((df["Quantity"] < 0).sum())

    # --- f) Invalid prices / quantities ----------------------------------
    bad_price = df["UnitPrice"] <= 0
    report["invalid_unitprice_rows"] = int(bad_price.sum())
    df = df[df["UnitPrice"] > 0]

    # --- g) Outlier guard on quantity ------------------------------------
    # Quantities above the 99.9th percentile are almost always data-entry
    # errors (a customer "ordering" 80,000 units). We winsorise rather than
    # delete so we keep the customer's existence in the base.
    qty_cap = df.loc[~df["IsReturn"], "Quantity"].quantile(0.999)
    report["quantity_cap_999"] = float(qty_cap)
    df.loc[(~df["IsReturn"]) & (df["Quantity"] > qty_cap), "Quantity"] = qty_cap
    df = df[df["Quantity"] != 0]

    # --- h) Derived revenue ----------------------------------------------
    df["TotalPrice"] = df["Quantity"] * df["UnitPrice"]

    report["clean_rows"] = len(df)
    report["clean_customers"] = df["CustomerID"].nunique()
    report["date_min"] = str(df["InvoiceDate"].min())
    report["date_max"] = str(df["InvoiceDate"].max())
    return df, report


# ---------------------------------------------------------------------------
# 2. Descriptive statistics
# ---------------------------------------------------------------------------
def descriptive_stats(df: pd.DataFrame) -> dict:
    """Headline business metrics on the cleaned transactions."""
    purchases = df[~df["IsReturn"]]  # revenue-generating lines only
    orders = purchases.groupby("InvoiceNo")["TotalPrice"].sum()
    per_customer = purchases.groupby("CustomerID")["TotalPrice"].sum()

    # ~2 year window -> annualised CLV proxy
    span_days = (df["InvoiceDate"].max() - df["InvoiceDate"].min()).days or 1
    span_years = span_days / 365.25

    return {
        "total_revenue": float(purchases["TotalPrice"].sum()),
        "total_orders": int(purchases["InvoiceNo"].nunique()),
        "total_customers": int(purchases["CustomerID"].nunique()),
        "avg_order_value": float(orders.mean()),
        "median_order_value": float(orders.median()),
        "avg_purchase_value_per_customer": float(per_customer.mean()),
        "median_purchase_value_per_customer": float(per_customer.median()),
        "avg_orders_per_customer": float(
            purchases.groupby("CustomerID")["InvoiceNo"].nunique().mean()
        ),
        "avg_customer_lifetime_value": float(per_customer.mean()),
        "annualised_clv": float(per_customer.mean() / span_years),
        "observation_window_years": round(span_years, 2),
        "repeat_purchase_rate": float(
            (purchases.groupby("CustomerID")["InvoiceNo"].nunique() > 1).mean()
        ),
    }


# ---------------------------------------------------------------------------
# 3. RFM features
# ---------------------------------------------------------------------------
def build_rfm(df: pd.DataFrame, snapshot: pd.Timestamp | None = None) -> pd.DataFrame:
    """
    Build the customer-level RFM table.

    R = days since last purchase (lower is better)
    F = number of distinct invoices (orders)
    M = total net revenue
    Returns are netted off so a customer who bought 10 and returned 3 is
    scored on 7.
    """
    customer_df = df[df["CustomerID"].notna()].copy()
    if snapshot is None:
        # Snap one day after the last observed transaction.
        snapshot = customer_df["InvoiceDate"].max() + pd.Timedelta(days=1)

    grouped = customer_df.groupby("CustomerID")

    rfm = pd.DataFrame(
        {
            "Recency": (snapshot - grouped["InvoiceDate"].max()).dt.days,
            "Frequency": grouped["InvoiceNo"].nunique(),
            "Monetary": grouped["TotalPrice"].sum(),
        }
    )

    # Average order value and tenure add nuance for profiling / scatter plots
    rfm["AvgOrderValue"] = rfm["Monetary"] / rfm["Frequency"].replace(0, np.nan)
    rfm["TenureDays"] = (
        snapshot - grouped["InvoiceDate"].min()
    ).dt.days
    rfm["SnapshotDate"] = snapshot

    rfm = rfm.replace([np.inf, -np.inf], np.nan)
    rfm["AvgOrderValue"] = rfm["AvgOrderValue"].fillna(rfm["Monetary"])
    rfm = rfm.dropna(subset=["Recency", "Frequency", "Monetary"])

    # Drop non-positive monetary values - they distort log/scale transforms
    rfm = rfm[rfm["Monetary"] > 0]
    return rfm


def rfm_quintiles(rfm: pd.DataFrame) -> pd.DataFrame:
    """Classic 1-5 RFM scoring for interpretability (R reversed so 5 = best)."""
    out = rfm.copy()
    out["R_Score"] = pd.qcut(
        out["Recency"], 5, labels=[5, 4, 3, 2, 1], duplicates="drop"
    ).astype(int)
    out["F_Score"] = pd.qcut(
        out["Frequency"].rank(method="first"), 5, labels=[1, 2, 3, 4, 5],
        duplicates="drop",
    ).astype(int)
    out["M_Score"] = pd.qcut(
        out["Monetary"].rank(method="first"), 5, labels=[1, 2, 3, 4, 5],
        duplicates="drop",
    ).astype(int)
    out["RFM_Score"] = out["R_Score"] + out["F_Score"] + out["M_Score"]
    out["RFM_Segment"] = (
        out["R_Score"].astype(str)
        + out["F_Score"].astype(str)
        + out["M_Score"].astype(str)
    )
    return out


# ---------------------------------------------------------------------------
# 4. Feature selection + scaling
# ---------------------------------------------------------------------------
FEATURES = ["Recency", "Frequency", "Monetary"]


def scale_features(
    rfm: pd.DataFrame, features: list[str] | None = None, log_transform: bool = True
) -> tuple[np.ndarray, StandardScaler, pd.DataFrame]:
    """
    Standardise the chosen behavioural features.

    Recency/Frequency/Monetary are all heavily right-skewed (a handful of
    wholesale buyers spend 100x the median). A log1p transform before
    StandardScaler stops those few customers from defining every centroid.
    Monetary is log-transformed on its absolute value to tolerate small
    negatives from heavy returns.
    """
    features = features or FEATURES
    X = rfm[features].copy()

    if log_transform:
        X = X.copy()
        X["Recency"] = np.log1p(X["Recency"])
        X["Frequency"] = np.log1p(X["Frequency"])
        X["Monetary"] = np.sign(X["Monetary"]) * np.log1p(X["Monetary"].abs())

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    X_scaled_df = pd.DataFrame(X_scaled, columns=features, index=rfm.index)
    return X_scaled, scaler, X_scaled_df


# ---------------------------------------------------------------------------
# 5. Choosing K
# ---------------------------------------------------------------------------
def evaluate_k(X_scaled: np.ndarray, k_range: range = range(2, 11)) -> pd.DataFrame:
    """Return inertia (elbow) and silhouette score for each candidate K."""
    results = []
    for k in k_range:
        km = KMeans(n_clusters=k, random_state=RANDOM_STATE, n_init=10)
        labels = km.fit_predict(X_scaled)
        results.append(
            {
                "k": k,
                "inertia": km.inertia_,
                "silhouette": silhouette_score(X_scaled, labels),
            }
        )
    return pd.DataFrame(results)


def pick_k(elbow_df: pd.DataFrame) -> int:
    """
    Choose K by maximising the silhouette score while requiring the elbow to
    have genuinely flattened (marginal inertia drop < 25% of the previous drop).
    """
    inertia = elbow_df["inertia"].to_numpy()
    drops = -np.diff(inertia)
    rel_drops = drops / drops[0]

    candidates = []
    for i in range(1, len(rel_drops)):
        if rel_drops[i] < 0.25:  # elbow has flattened by this point
            candidates.append(elbow_df["k"].iloc[i + 1])

    if candidates:
        sub = elbow_df[elbow_df["k"].isin(candidates)]
        return int(sub.loc[sub["silhouette"].idxmax(), "k"])
    return int(elbow_df.loc[elbow_df["silhouette"].idxmax(), "k"])


# ---------------------------------------------------------------------------
# 6. Fit K-Means
# ---------------------------------------------------------------------------
def fit_kmeans(
    X_scaled: np.ndarray, rfm: pd.DataFrame, k: int, features: list[str] | None = None
) -> tuple[KMeans, pd.DataFrame]:
    features = features or FEATURES
    km = KMeans(n_clusters=k, random_state=RANDOM_STATE, n_init=10)
    labels = km.fit_predict(X_scaled)

    out = rfm.copy()
    out["Cluster"] = labels
    out["DistanceToCentroid"] = np.linalg.norm(
        X_scaled - km.cluster_centers_[labels], axis=1
    )
    return km, out


# ---------------------------------------------------------------------------
# 7. Profiling
# ---------------------------------------------------------------------------
def profile_clusters(rfm_clustered: pd.DataFrame, features: list[str] | None = None) -> pd.DataFrame:
    """Mean feature values, sizes and revenue share per cluster."""
    features = features or FEATURES
    total_rev = rfm_clustered["Monetary"].sum()

    profile = rfm_clustered.groupby("Cluster").agg(
        Customers=("Monetary", "size"),
        Recency=("Recency", "mean"),
        Frequency=("Frequency", "mean"),
        Monetary=("Monetary", "mean"),
        AvgOrderValue=("AvgOrderValue", "mean"),
        TenureDays=("TenureDays", "mean"),
    )
    profile["Recency"] = profile["Recency"].round(1)
    profile["Frequency"] = profile["Frequency"].round(2)
    profile["Monetary"] = profile["Monetary"].round(2)
    profile["AvgOrderValue"] = profile["AvgOrderValue"].round(2)
    profile["TenureDays"] = profile["TenureDays"].round(0)

    profile["Revenue"] = rfm_clustered.groupby("Cluster")["Monetary"].sum().round(2)
    profile["CustomerShare_%"] = (profile["Customers"] / len(rfm_clustered) * 100).round(1)
    profile["RevenueShare_%"] = (profile["Revenue"] / total_rev * 100).round(1)
    profile = profile.sort_values("Monetary", ascending=False)

    # Attach the whole-base medians so label_clusters() can set thresholds on
    # the real customer distribution rather than on cluster means alone.
    profile.attrs["base_recency"] = float(rfm_clustered["Recency"].median())
    profile.attrs["base_frequency"] = float(rfm_clustered["Frequency"].median())
    profile.attrs["base_monetary"] = float(rfm_clustered["Monetary"].median())
    return profile


def label_clusters(profile: pd.DataFrame) -> dict[int, str]:
    """
    Assign an interpretable business name to each cluster.

    Rather than hard thresholds on raw values (which break because clusters
    differ wildly in scale), we rank the clusters on each RFM axis relative
    to each other and name the segment that the resulting pattern describes:

        recent + frequent + high value    -> Champions
        recent + (frequent or high value) -> Loyal Customers
        recent only                       -> New / Promising
        stale + frequent + high value     -> At Risk - High Value
        stale + one of the two            -> At Risk - Needs Attention
        stale + low on both               -> Hibernating / Lost
    """
    feats = ["Recency", "Frequency", "Monetary"]
    means = profile[feats].copy()

    # Use the whole customer base to set thresholds, not just the cluster
    # means. Cluster means on a skewed base sit far above the median, so a
    # mid-point taken across cluster means would call a solid 1,169-spend
    # cluster "low value". Anchoring on the base distribution avoids that.
    base_r = profile.attrs.get("base_recency")
    base_f = profile.attrs.get("base_frequency")
    base_m = profile.attrs.get("base_monetary")

    def threshold(value, fallback, factor):
        anchor = fallback if value is None else value
        return anchor * factor
    # Fall back to the cluster-mean median if base stats were not attached.
    r_cut = threshold(base_r, means["Recency"].median(), 1.0)      # still active?
    f_cut = threshold(base_f, means["Frequency"].median(), 1.0)    # orders per customer
    m_cut = threshold(base_m, means["Monetary"].median(), 1.0)     # revenue per customer
    # The single highest-spending cluster is the VIP tier. "Champions" has to
    # mean the best customers, not merely "above the median", otherwise every
    # healthy cluster ends up with the same name.
    top_value_cluster = means["Monetary"].idxmax()
    # A cluster is a genuine high roller if it outspends the typical customer
    # by a wide margin (3x the base median).
    VIP_MULTIPLE = 3.0
    labels = {}
    for cid in profile.index:
        r_hi = means.loc[cid, "Recency"] <= r_cut
        f_hi = means.loc[cid, "Frequency"] >= f_cut
        m_hi = means.loc[cid, "Monetary"] >= m_cut
        is_vip = (
            cid == top_value_cluster
            and means.loc[cid, "Monetary"] >= m_cut * VIP_MULTIPLE
        )
        if is_vip and r_hi and f_hi:
            labels[cid] = "Champions"
        elif r_hi and f_hi and m_hi:
            labels[cid] = "Loyal Customers"
        elif r_hi and (f_hi or m_hi):
            labels[cid] = "Promising / Developing"
        elif r_hi:
            labels[cid] = "New / Promising"
        elif f_hi and m_hi:
            labels[cid] = "At Risk - High Value"
        elif f_hi or m_hi:
            labels[cid] = "At Risk - Needs Attention"
        else:
            labels[cid] = "Hibernating / Lost"

    # Resolve collisions deterministically by revenue: the highest-revenue
    # cluster of a tied pair keeps the clean name, and the runner-up gets a
    # qualifier that tells you which axis it is weaker on.
    order = profile["Revenue"].sort_values(ascending=False).index.tolist()
    seen: dict[str, int] = {}
    for cid in order:
        name = labels[cid]
        seen[name] = seen.get(name, 0) + 1
        if seen[name] > 1:
            weaker = "lower spend" if (
                means.loc[cid, "Monetary"] < means["Monetary"].median()
            ) else "less frequent"
            labels[cid] = f"{name} ({weaker})"
    return labels


# ---------------------------------------------------------------------------
# 8. Plots
# ---------------------------------------------------------------------------
def plot_elbow(elbow_df: pd.DataFrame, chosen_k: int, save_dir: str = OUT_DIR) -> str:
    fig, axes = plt.subplots(1, 2, figsize=(13, 4.6))

    axes[0].plot(elbow_df["k"], elbow_df["inertia"], marker="o", lw=2, color="#2E5C8A")
    axes[0].axvline(chosen_k, ls="--", color="crimson", lw=1.6,
                    label=f"Chosen K = {chosen_k}")
    axes[0].set_title("Elbow Method - Inertia (WCSS) vs K")
    axes[0].set_xlabel("Number of clusters (K)")
    axes[0].set_ylabel("Inertia (within-cluster sum of squares)")
    axes[0].legend()

    axes[1].plot(elbow_df["k"], elbow_df["silhouette"], marker="s", lw=2,
                 color="#1B8A5A")
    axes[1].axvline(chosen_k, ls="--", color="crimson", lw=1.6,
                    label=f"Chosen K = {chosen_k}")
    axes[1].set_title("Silhouette Score vs K")
    axes[1].set_xlabel("Number of clusters (K)")
    axes[1].set_ylabel("Silhouette score (higher = better)")
    axes[1].legend()

    fig.suptitle("Determining the Optimal Number of Clusters", fontsize=13, y=1.03)
    path = os.path.join(save_dir, "01_elbow_method.png")
    fig.savefig(path)
    plt.close(fig)
    return path


def plot_scatter_combinations(
    rfm_clustered: pd.DataFrame,
    save_dir: str = OUT_DIR,
    label_map: dict[int, str] | None = None,
) -> list[str]:
    """Scatter plots across the feature combinations that matter."""
    paths = []
    plot_df = rfm_clustered.copy()
    # Use business names in the legend so the charts are self-explanatory.
    if label_map:
        plot_df["Segment"] = plot_df["Cluster"].map(label_map)
    combos = [
        ("Recency", "Frequency",
         "Recency (days, lower = more recent)", "Frequency (orders)"),
        ("Frequency", "Monetary",
         "Frequency (orders)", "Monetary (total revenue)"),
        ("Recency", "Monetary",
         "Recency (days, lower = more recent)", "Monetary (total revenue)"),
    ]

    for i, (x, y, xlab, ylab) in enumerate(combos, start=1):
        fig, ax = plt.subplots(figsize=(7.8, 5.6))
        hue = "Segment" if label_map else "Cluster"
        sns.scatterplot(
            data=plot_df, x=x, y=y, hue=hue,
            palette="tab10", s=28, alpha=0.7, edgecolor="none", ax=ax,
        )
        # Log scale for the long-tailed monetary axis
        if y in ("Monetary",):
            ax.set_yscale("log")
        ax.set_title(f"Cluster Separation: {x} vs {y}")
        ax.set_xlabel(xlab)
        ax.set_ylabel(ylab + (" (log scale)" if y == "Monetary" else ""))
        ax.legend(title="Segment" if label_map else "Cluster",
                  bbox_to_anchor=(1.02, 1), loc="upper left", frameon=True,
                  fontsize=8)
        path = os.path.join(save_dir, f"0{i+1}_scatter_{x}_vs_{y}.png")
        fig.savefig(path)
        plt.close(fig)
        paths.append(path)
    return paths


def plot_cluster_sizes(rfm_clustered: pd.DataFrame, label_map: dict[int, str],
                       save_dir: str = OUT_DIR) -> str:
    counts = (
        rfm_clustered["Cluster"]
        .value_counts()
        .sort_index()
        .rename(index=label_map)
    )
    fig, ax = plt.subplots(figsize=(9, 5))
    bars = ax.bar(counts.index.astype(str), counts.values,
                  color=sns.color_palette("deep", len(counts)))
    for bar, val in zip(bars, counts.values):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 3,
                f"{val:,}\n({val / counts.sum() * 100:.1f}%)",
                ha="center", va="bottom", fontsize=9)
    ax.set_title("Number of Customers per Cluster")
    ax.set_ylabel("Number of customers")
    ax.set_xlabel("Cluster (business label)")
    ax.set_ylim(0, counts.max() * 1.18)
    plt.setp(ax.get_xticklabels(), rotation=18, ha="right")
    path = os.path.join(save_dir, "05_customers_per_cluster.png")
    fig.savefig(path)
    plt.close(fig)
    return path


def plot_cluster_profiles(rfm_clustered: pd.DataFrame, label_map: dict[int, str],
                          save_dir: str = OUT_DIR) -> str:
    """Heatmap of z-scored cluster means - shows what defines each segment."""
    feats = ["Recency", "Frequency", "Monetary", "AvgOrderValue"]
    means = rfm_clustered.groupby("Cluster")[feats].mean()
    z = (means - means.mean()) / means.std(ddof=0)
    z.index = [f"{label_map[c]}" for c in z.index]

    fig, ax = plt.subplots(figsize=(8, 0.7 * len(z) + 2))
    sns.heatmap(z, annot=True, fmt=".2f", cmap="RdYlGn_r", center=0,
                linewidths=0.6, cbar_kws={"label": "z-score vs cluster average"},
                ax=ax)
    ax.set_title("Cluster Profiles - Standardised Mean Feature Values")
    ax.set_xlabel("")
    ax.set_ylabel("")
    path = os.path.join(save_dir, "06_cluster_profile_heatmap.png")
    fig.savefig(path)
    plt.close(fig)
    return path


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------
MARKETING_ACTIONS = {
    "Champions": (
        "Reward and retain. VIP/loyalty tier with early access to new drops, "
        "free express shipping and a personal account manager for the top "
        "spenders. Ask for reviews and referrals -- they are your best "
        "advocates. Avoid discounting; it only trains them to wait for sales."
    ),
    "Loyal Customers": (
        "Increase share of wallet. Cross-sell premium and complementary "
        "categories, offer bundle upgrades, a replenishment/subscription "
        "option and free-shipping thresholds set just above their current "
        "average order value. They already trust you -- grow basket size, "
        "not discount depth."
    ),
    "Promising / Developing": (
        "Nurture toward loyal status. Nudge the weaker axis: if frequency is "
        "low, drive a second/third order with a short-window incentive; if "
        "value is low, use recommendations and bundles to trade them up. "
        "Targeted email flows beat blanket discounts here."
    ),
    "New / Promising": (
        "Onboard and convert to repeat. Strong welcome series in the first "
        "30 days, a time-limited second-purchase incentive, and educational "
        "content that drives the next order before the habit is lost."
    ),
    "At Risk - High Value": (
        "Urgent win-back. High historical spend but gone quiet -- trigger an "
        "automated win-back email with a meaningful, personal offer, ask "
        "what went wrong, and flag for human outreach if the value is high "
        "enough. This segment is the single biggest recoverable revenue pool."
    ),
    "At Risk - Needs Attention": (
        "Re-engage cheaply. 'We miss you' campaign with a low-cost incentive "
        "and a reminder of their most-bought items. Survey to find the "
        "friction; if they do not respond in 90 days, move them to "
        "low-cost nurture only."
    ),
    "Hibernating / Lost": (
        "Minimise spend or sunset. Do not include in paid campaigns -- the "
        "cost per reactivation exceeds expected value. A single low-cost "
        "seasonal email is the limit; otherwise suppress to protect "
        "deliverability and margin."
    ),
}


def run(data_path: str = DATA_PATH, out_dir: str = OUT_DIR, make_plots: bool = True) -> dict:
    os.makedirs(out_dir, exist_ok=True)
    df, qa = load_and_clean(data_path)
    stats = descriptive_stats(df)
    rfm = build_rfm(df)
    rfm_q = rfm_quintiles(rfm)
    X_scaled, scaler, _ = scale_features(rfm)
    elbow_df = evaluate_k(X_scaled)
    k = pick_k(elbow_df)
    km, rfm_clustered = fit_kmeans(X_scaled, rfm, k)
    profile = profile_clusters(rfm_clustered)
    label_map = label_clusters(profile)
    profile["Segment"] = profile.index.map(label_map)
    profile = profile.set_index("Segment", drop=False)

    paths = []
    if make_plots:
        paths.append(plot_elbow(elbow_df, k, out_dir))
        paths.extend(plot_scatter_combinations(rfm_clustered, out_dir, label_map))
        paths.append(plot_cluster_sizes(rfm_clustered, label_map, out_dir))
        paths.append(plot_cluster_profiles(rfm_clustered, label_map, out_dir))

    rfm_clustered["Segment"] = rfm_clustered["Cluster"].map(label_map)

    # Persist artefacts for the notebook / report
    rfm_clustered.to_csv(os.path.join(out_dir, "rfm_clustered.csv"))
    rfm_q.to_csv(os.path.join(out_dir, "rfm_scored.csv"))
    profile.to_csv(os.path.join(out_dir, "cluster_profiles.csv"))
    elbow_df.to_csv(os.path.join(out_dir, "elbow_silhouette.csv"), index=False)

    return {
        "df": df,
        "qa": qa,
        "stats": stats,
        "rfm": rfm,
        "rfm_scored": rfm_q,
        "elbow": elbow_df,
        "k": k,
        "km": km,
        "clustered": rfm_clustered,
        "profile": profile,
        "labels": label_map,
        "plot_paths": paths,
        "silhouette": float(
            silhouette_score(X_scaled, rfm_clustered["Cluster"])
        ),
    }


if __name__ == "__main__":
    res = run()
    pd.set_option("display.width", 160)
    print("=" * 78)
    print("DATA QUALITY REPORT")
    print("=" * 78)
    for k_, v in res["qa"].items():
        print(f"  {k_:<28} {v}")
    print("\n" + "=" * 78)
    print("DESCRIPTIVE STATISTICS")
    print("=" * 78)
    for k_, v in res["stats"].items():
        print(f"  {k_:<38} {v:,.2f}" if isinstance(v, float) else f"  {k_:<38} {v}")
    print("\n" + "=" * 78)
    print(f"ELBOW / SILHOUETTE  ->  chosen K = {res['k']}")
    print("=" * 78)
    print(res["elbow"].to_string(index=False))
    print(f"\nFinal silhouette score: {res['silhouette']:.3f}")
    print("\n" + "=" * 78)
    print("CLUSTER PROFILES")
    print("=" * 78)
    print(res["profile"].to_string())
    print("\nPlots written:")
    for p in res["plot_paths"]:
        print("  ", p)
