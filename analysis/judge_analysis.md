## Judge Analysis Plan & Methodology

### Aims and considerations
- Voters want to understand how judges rule on the issues they care about; our analysis should surface patterns in how judges have voted on cases related to our selection of relevant rights
- Placing judges in context: how many times has this judge ruled to protect this right compared to other judges in the same court? Compared to all judges at the same level, or in the same state?
- Voting history can reveal ideological alignment, including in states with nonpartisan judicial selection methods: our analysis should highlight similarity and dissimilarity between judges

### Analysis tools
- SPACEJAM: ``DW-NOMINATE for judges'' - calculate similarity score based on voting record and visualize in 2D space
- Polarization choropleth
- Radar charts

#### SPACEJAM - MDS & Clustering

MDS (Multi-Dimensional Scaling) methods take either a feature matrix or a dissimilarity matrix, calculate dissimilarity and project distances into a smaller number of dimensions (usually 1-2 for visualization). We use the `sklearn.manifold.MDS` model from `scikit-learn` to project a matrix of judge votes on cases into a 2-dimensional space to show similarity/dissimilarity between judges.

Our SPACEJAM analysis is inspired by [Voteview](https://voteview.com/) and [DW-NOMINATE](https://en.wikipedia.org/wiki/NOMINATE_(scaling_method)), a method for analyzing legislative roll-call voting behavior. The NOMINATE method uses a model of legislator utility functions in combination with multi-dimensional scaling to analyze legislator behavior. We use rulings by judges on the same court on the same cases as an equivalent to roll-call voting, and apply MDS to the resulting feature matrix.

Further reading: [Spatial Models of Parliamentary Voting, Keith T. Poole](https://www.cambridge.org/core/books/spatial-models-of-parliamentary-voting/4459C452C3CAF54DD5CB8720F33B2DA0)

Challenges:
- This method can only be run on complete feature matrices, ie every judge votes on every case. Currently, we restrict to only cases which all current supreme court justices voted on. We should include checks to ensure the analysis is not run on very small numbers of cases, possibly skewing the results.
- Coding rulings - choices need to be made about how to code various rulings. In v1, we only consider concurrence and dissents. We could consider coding different types of concurrence with different weights (partial dissent, multiple concurring opinions, etc). We could also handle unanimous decisions differently to split decisions.

Future development:
- Integrate some kind of random sampling to understand how variable the results are based on which cases are chosen for comparison
- Integrate a model of judge preference, as in DW-NOMINATE, in addition to simple voting history
- Re-evaluate concurrence/dissent coding
