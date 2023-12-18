# Video searcher
The Video searcher is implemented in neural-functionalities/video_searcher. The main `VideoSearcher` object and functionality is defined in video_searcher.py, with servicer and abstract classes also defined within the folder.

Stores data on the videos available to search from in ‘videos_metadata.json’, when initiated it reads this file and pre-computes sbert embeddings for all video titles using 'all-MiniLM-L6-v2' sentence transformer model, which is stored and used for embedding queries also.

## Method: search_video
This method provides the main functionality of the class, allowing to search for a video given a `VideoQuery` object.
### Input parameter: VideoQuery
`VideoQuery` is an object responsible for storing information about the given query that needs to be processed when searching for a corresponding video to  a step. Definition from shared/protobufs/video_searcher.proto:
```
VideoQuery {
  string text = 1; # query text 
  int32 top_k = 2; # number of search results 
  Session.Domain domain = 3; # domain of query (cooking or DIY)
}
```
### Search method and logic
The searcher uses an sbert sentence transformer to embed the query text field, and uses cosine similarity to compare query to the video titles. Possible video titles are sorted in order of similarity, and if the one with the highest is over 0.7 threshold, a `VideoDocument` object is returned.

### Output parameter: VideoDocument
`VideoObject` is an object responsible for storing all the useful information information about a video returned from the searcher. The information stored in the object is defined in protobufs as:
```
message VideoDocument {
    string doc_id = 1; // Unique identifier for each document.
    string title = 2; // Title of task being completed.
    string url = 3;  // URL that the input data was extracted.
    string video_url = 4;
    string thumbnail = 5;
    string hosted_mp4 = 6;
    string uploader = 7;
    int32 views = 8;
    int32 duration = 9;
    string description = 10;
    string youtube_id = 11;
    string subtitles = 12;
}
```

## Usage in orchestrator/policy/execution_policy.py

### Method: __retrieve_video
Defined at lines 103-135, this method is called when the orchestrator decides that a video should be retrieved. Then it performs the following tasks to retrieve a video for display:
- Get the current step text by creating a `TMRequest` object initialised with the current session and state, then calling the task manager with this request to get the current taskmap node and extract the current step text. 
- If the current step node has a pre-made query stored in its 'caption_query' field then this is used as input to the video searcher, otherwise a new  query is built.
- If a new query needs constructed then action classification is attempted on the current step text. This involves calling the action classifier (functionalities/action_method_classifer) which tries to detect any action present in the step from a known bank of actions and return this information as an ActionClassification object, to remove noise present in the step text and improve the quality of search results returned from the query. 
- If there are multiple actions in one step, one of them is selected at random to form the query. If none are present, no query is returned and no search is performed.
- If a valid query is generated, the `search_video` method of the video searcher is called and the result is loaded into a `Video` object and returned to be displayed.

### Triggering video retrieval
There are two ways to trigger a video in the local client:
- Lines 353-371 check if a ‘DetailsIntent’ is triggered or if the utterances 'more details', 'details', 'show me more’ were included in the interaction. If so, and the device has ability to show video (not headless) then the __retrive_video method is called to get the video to display.
- Lines 428-436: In the current system the, `__retrieve_video` is called at each step of the task, so every step is check for an action using the action classifier and if one is found, a query is created and a video is searched for and possibly returned. This allows the system to suggest the video to the user automatically at each step to improve the user experience.

### Displaying retrived videos
After a video is returned from the searcher, the orchestrator makes use of the following methods:

**MergeFrom:**
Takes a `Video` object and adds it to the screen using the protobuf method `MergeFrom` to update the output object to include the data from the video found in the search in the fields of the ouput.video object.

**build_video_button:**
Takes the found video object and output object updated with the video and generates response speech text which suggests the video found for the current step to the user. Then buttons are added to the screen object for playing the video and skipping to the next step. The output speech and screen are returned, and these are added into the session output object.

These methods updated the required attributes in the session output object to display the video to the user, and allow them to choose to play it or not. If the user clicks the play button, then in lines 225-245 the screen output format is altered to video and the found video is played, whilst the main interaction is paused. If the screen output video field wasn't filled (i.e no relevant video found) then the user is told that no relevant videos were found.