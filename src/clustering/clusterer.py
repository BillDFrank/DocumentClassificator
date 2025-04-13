import streamlit as st
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import OneHotEncoder
from src.utilities.helpers import persist_labels, calculate_similarity, propose_cluster_names
import os

# Update the path to match the location where the embedding app saves the file
PARQUET_FILE = os.path.join("data", "processed", "embeddings_labeled.parquet")


def perform_clustering(df, n_clusters):
    """Performs K-Means clustering on the dataset."""
    if df.empty:
        return None, None

    # Feature Engineering
    enc = OneHotEncoder(handle_unknown="ignore")
    X = enc.fit_transform(df[['combined_text']]).toarray()

    # Apply K-Means
    kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    df["cluster"] = kmeans.fit_predict(X)

    return df, kmeans


def app():
    st.title("Clustering")
    st.write("Suggests clusters to facilitate classification.")

    st.sidebar.title("Settings")
    n_similares = st.sidebar.slider("Number of Similar Elements", 1, 30, 10)
    n_clusters = st.sidebar.slider("Number of Clusters", 2, 50, 10)
    submit_button = st.sidebar.button("Submit")

    # Load DataFrame from Parquet file
    if "df" not in st.session_state:
        if not os.path.exists(PARQUET_FILE):
            st.error(
                f"File '{PARQUET_FILE}' not found. Generate the embeddings first.")
            return
        else:
            st.session_state.df = pd.read_parquet(PARQUET_FILE)

    # Perform clustering only when "Submit" is clicked
    if submit_button:
        df = st.session_state.df
        df, kmeans = perform_clustering(df, n_clusters)

        if df is not None:
            df = calculate_similarity(df, n_clusters)
            st.session_state.df = df
            st.session_state.cluster = 0
            st.success("Clustering completed successfully!")

    # If clustering has been performed, show the labeling interface
    if "cluster" in st.session_state:
        df = st.session_state.df
        distinct_labels = df['label'].unique().tolist()
        distinct_labels = [x for x in distinct_labels if x is not None]
        distinct_labels.sort()
        df['label'] = df['label'].fillna("")
        df = df[df['label'] == ""]
        cluster = st.session_state.cluster

        st.header("Parameters")
        st.write(f"Displaying {n_similares} similar elements")
        st.write(f"Cluster: {cluster+1} of {n_clusters}")
        labels_count = df.shape[0]
        empty_labels_count = df['label'].eq("").sum()
        st.write(
            f"Number of elements without a label: {empty_labels_count}/{labels_count}")

        next_back_cols = st.columns([1, 1, 2])
        with next_back_cols[0]:
            if st.button("BACK"):
                st.session_state.cluster = (cluster - 1) % n_clusters
                cluster = st.session_state.cluster
        with next_back_cols[1]:
            if st.button("NEXT"):
                st.session_state.cluster = (cluster + 1) % n_clusters
                cluster = st.session_state.cluster

        similar_docs = df[(df['cluster'] == cluster) & (df['label'] == "")]
        similar_docs = similar_docs.head(n_similares)

        st.header("Selection of Cluster Labels")

        if 'existing_labels' not in st.session_state:
            if len(distinct_labels) < 2:
                st.session_state.existing_labels = [
                    "CONFIDENTIAL", "NOT CONFIDENTIAL"
                ]
                st.session_state.existing_labels.sort()
            else:
                st.session_state.existing_labels = distinct_labels

        label_cols = st.columns([2, 3, 2])
        with label_cols[0]:
            selected_label = st.selectbox(
                "Select a label", st.session_state.existing_labels)
        with label_cols[1]:
            new_label = st.text_input("Add New Label")
        with label_cols[2]:
            if st.button("Add Label"):
                if new_label and new_label not in st.session_state.existing_labels:
                    st.session_state.existing_labels.append(new_label)
                    selected_label = new_label
                    st.success(f"Label '{new_label}' added successfully.")

        st.header("Similar Elements in the Cluster")

        selected_similars = []
        for idx, row in similar_docs.iterrows():
            if st.checkbox(f"{row['combined_text'][0:1000]}", key=idx, value=True):
                selected_similars.append(idx)

        if st.button("LABEL"):
            for idx in selected_similars:
                st.session_state.df.at[idx, 'label'] = selected_label

            try:
                st.session_state.df.to_parquet(PARQUET_FILE, index=False)
                st.success("Elements labeled successfully and file updated!")
            except Exception as e:
                st.error(f"Error saving file: {e}")


if __name__ == "__main__":
    app()
