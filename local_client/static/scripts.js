encodeDictInURI = (dict) => {
    uri = ""
    var esc = encodeURIComponent;

    for (const [key, value] of Object.entries(dict))
    {
        uri += esc(key) + "=" + esc(value) + "&"
    }
    return uri

}

const searchForm = document.querySelector("#search-form");
const searchFormInput = document.querySelector("input");

const speechForm = document.querySelector("#speechbar")

const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
let speech = new SpeechSynthesisUtterance();
speech.lang = "en";

if (SpeechRecognition){
    console.log("Your browser supports sr");

    // adding the mic button if browser supports
    // searchForm.insertAdjacentHTML("afterbegin", '<button type="button" id="speechbutton"><i class="fas fa-microphone"></i></button>');
    const micBtn = speechForm.querySelector("button");
    const micIcon = micBtn.querySelector("i");

    const recognition = new SpeechRecognition();
    recognition.continous = true;


    micBtn.addEventListener("click", micBtnClick);
    function micBtnClick () {
        if (micIcon.classList.contains("fa-microphone")) {
            recognition.start();
        }
        else {
            
            recognition.stop();
        }
    }
    recognition.addEventListener("start", startSpeechRecognition);
    function startSpeechRecognition() {
        micIcon.classList.remove("fa-microphone");
        micIcon.classList.add("fa-microphone-slash");
        searchFormInput.focus();
        console.log("Speech recognition started");
    }

    recognition.addEventListener("end", endSpeechRecognition);
    function endSpeechRecognition() {
        micIcon.classList.add("fa-microphone");
        micIcon.classList.remove("fa-microphone-slash");
        searchFormInput.focus();
        console.log("Speech recognition ended");
    }

    recognition.addEventListener("result", resultOfSpeechRecognition); //<==> recognition.onresult = function(event) {....}
    function resultOfSpeechRecognition(event) {
        console.log(event);
        const currentResultIndex = event.resultIndex
        const transcript = event.results[currentResultIndex][0].transcript;
        searchFormInput.value = transcript;

        const call = async () => {

            data = {
                text : searchFormInput.value||document.getElementById('textInput').value,
                id   : document.getElementById('IDField').value,
                headless: 'false',
            }
        
            const response = await fetch('/getresponse?'+ encodeDictInURI(data));
            const myJson = await response.json();

            let speech = new SpeechSynthesisUtterance();
            speech.lang = "en";

            speech.text = myJson['speechText'];
            speech.rate = 0.009;
            window.speechSynthesis.speak(speech);
        
            myJson['speechText'] = myJson['speechText'].replace(/[\.\:] /g, "<br/>")
            console.log(myJson)

            display("User", searchFormInput.value)
            display("BOT", myJson['speechText'])

            renderScreen(myJson['screen'], myJson['template'])
            document.getElementById('textInput').value = ''
        }

        if (transcript.toLowerCase().trim()=="stop recording") {
            recognition.stop();
        }
        else if (!searchFormInput.value) {
            searchFormInput.value = transcript;
        }
        else {
            setTimeout(() => {
                call();
            }, 150);
        }
    }
}
else {
    console.log("your browser does not support");
}


const call = async () => {

    data = {
        text : document.getElementById('textInput').value,
        id   : document.getElementById('IDField').value,
        headless: 'false',
    }

    const response = await fetch('/getresponse?'+ encodeDictInURI(data));
    const myJson = await response.json();

    let speech = new SpeechSynthesisUtterance();
            speech.lang = "en";

            speech.text = myJson['speechText'];
            speech.rate = 0.009;
            window.speechSynthesis.speak(speech);

    myJson['speechText'] = myJson['speechText'].replace(/[\.\:] /g, "<br/>")
    console.log(myJson)
    display("User", document.getElementById('textInput').value)
    display("BOT", myJson['speechText'])

    renderScreen(myJson['screen'], myJson['template'])
    document.getElementById('textInput').value = ''
}

const renderScreen = (screen_interaction, extra_template) => {
    const format = screen_interaction['format'].toLowerCase()

    if (Object.keys(extra_template).length > 0) {
        displayBox = document.getElementById("displaybox")
        displayBox.innerHTML = extra_template
    }

    if ("imageList" in screen_interaction) {
        const image_list = screen_interaction['imageList']

        if (format === 'text_image') {
            let image_path = 'https://grill-bot-data.s3.amazonaws.com/images/multi_domain_default.jpg'
            if (image_list.length > 0) {
                image_path = image_list[0]['path']
            }
            document.getElementById('image').setAttribute('src', image_path)
        }
        if (format === 'image_carousel') {
            if (image_list.length > 0) {
                for (let i = 0, len = image_list.length; i < len; i++) {
                    image_box = document.getElementById('img' + i)
                    imageNode = image_box.querySelector('img')
                    imageNode.setAttribute('src', image_list[i]['path'])
                    imageNode.addEventListener('click', function() {
                        document.getElementById('inputText').value = screen_interaction['onClickList'][i];
                        call();
                    })
                    descriptionNode = image_box.querySelector('p')
                    descriptionNode.innerHTML = image_list[i]['description']
                }
            }
        }
    }

    titleNode = document.getElementById("title")
    if (titleNode != null) {
        titleNode.innerHTML = screen_interaction["headline"]
    }

    subheaderNode = document.getElementById("subheader")
    if (subheaderNode != null) {
        subheaderNode.innerHTML = screen_interaction["subheader"]
    }

    hintNode = document.getElementById("hint_text")
    if (hintNode != null) {
        hintNode.innerText = "Hint: Say \"" + screen_interaction["hintText"] + "\""
    }

    body = document.getElementById("paragraphs")
    if ("paragraphs" in screen_interaction) {
        for (let i = 0, len = screen_interaction["paragraphs"].length; i < len; i++) {
            body.innerHTML += screen_interaction["paragraphs"][i] + "<br>"
        }
    }
    if ("requirements" in screen_interaction) {
        body.innerHTML += "<h3> Requirements: </h3> <ul>"
        for (let i = 0, len = screen_interaction["requirements"].length; i < len; i++) {
            body.innerHTML += "<li>" + screen_interaction["requirements"][i] + "</li>"
        }
        body.innerHTML += "</ul>"
    }

    if (format === "VIDEO" && "video" in screen_interaction) {
        const video_obj = screen_interaction['imageList']
        const video_path = video_obj['hosted_mp4']
        document.getElementById('video').firstElementChild.setAttribute('src', video_path)
    }

    if ("buttons" in screen_interaction) {
        const buttons_box = document.getElementById('buttons');
        let buttons = buttons_box.querySelectorAll('button');
        for (let i = 0, len = screen_interaction['buttons'].length; i < len; i++) {
            buttons[i].innerText += screen_interaction["buttons"][i]
            buttons[i].addEventListener('click', function () {
                document.getElementById('textInput').value = screen_interaction["onClickList"][i];
                call();
            })
            buttons[i].style.display = ""
        }
    }
}

const display = (user, text) => {

    if (user=="BOT") {
        chatNode = document.getElementsByClassName("chat")[0]
        chatNode.innerHTML += "<p id='botStarterMessage'><span>" + text + "</span></p>";

        chatNode.scrollTop= chatNode.scrollHeight
    }

    else {
        chatNode = document.getElementsByClassName("chat")[0]
        chatNode.innerHTML += "<p id='usermessage'><span>" + text + "</span></p>";

        chatNode.scrollTop= chatNode.scrollHeight
    }
}

const assignID = () => {
    var id = Math.floor(Math.random() * Date.now()).toString(16)
    document.getElementById("IDField").value = "local_" + id
}