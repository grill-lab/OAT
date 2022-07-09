

encodeDictInURI = (dict) => {
    uri = ""
    var esc = encodeURIComponent;

    for (const [key, value] of Object.entries(dict))
    {
        uri += esc(key) + "=" + esc(value) + "&"
    }
    return uri

}

const call = async () => {

    data = {
        text : document.getElementById('inputText').value,
        id   : document.getElementById('IDField').value,
        headless: 'false',
    }

    const response = await fetch('/getresponse?'+ encodeDictInURI(data));
    const myJson = await response.json();

    myJson['speechText'] = myJson['speechText'].replace(/[\.\:] /g, "<br/>")
    console.log(myJson)
    display("User", document.getElementById('inputText').value)
    display("BOT", myJson['speechText'])

    renderScreen(myJson['screen'], myJson['template'])
    document.getElementById('inputText').value = ''
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
                document.getElementById('inputText').value = screen_interaction["onClickList"][i];
                call();
            })
            buttons[i].style.display = ""
        }
    }
}

const display = (user, text) => {

    chatNode = document.getElementsByClassName("chat")[0]
    chatNode.innerHTML += "<p> <strong>" + user + "</strong>: " + text + "</p>";

    chatNode.scrollTop= chatNode.scrollHeight

}

const assignID = () => {
    var id = Math.floor(Math.random() * Date.now()).toString(16)
    document.getElementById("IDField").value = "local_" + id
}