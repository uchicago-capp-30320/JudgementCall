## Judge Analysis Plan & Methodology

### Judge analysis wishlist
- "DW-NOMINATE for judges" - calculate similarity score based on voting record and visualize in 2D space
- Relative record - how many times has this judge ruled to protect eg environment vs other judges in the same court? vs all judges at the same level?
- Radar charts on selection of issues - overlap judges to compare
- Accessibility: dynamically generated description of main takeaways from chart

### Judge Map - MDS & Clustering
MDS (Multi-Dimensional Scaling) method takes either a feature matrix or a dissimilarity matrix, calculates dissimilarity and projects distances into a smaller number of dimensions (usually 1-2 for visualization). We use the `sklearn.manifold.MDS` model from `scikit-learn` to project a matrix of judge votes on cases into a 2-dimensional space to show similarity/dissimilarity between judges.
