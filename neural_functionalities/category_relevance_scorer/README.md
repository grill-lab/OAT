## Category Relevance Scorer

This functionality used to evaluate whether the retrieved categories are relevant given a user query. It sits between the `CategorySearcher` and the `Planner` Policy.

![Categories Architecture](../../doc/category_architecture.png)

Given a `CategorySearchResult`, we return a `CategoryDocument`. If the category in the search result is found as not relevant, we return an empty `CategoryDocument`.

A `CategorySearchResult` is defined as follows:
```protobuf
message CategorySearchResult{
  repeated CategoryDocument results = 1;
  string original_query_text = 2;
}
```

Using sentence transformers, we calculate the string similarity between the user query and the category result.
