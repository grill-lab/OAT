

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

    const source = myJson['source']
    // remove the common suffixes for policy module names
    let policy = source['policy'].split('|')[0].replace('_policy', '').replace('_handler', '')
    // construct the string displayed if you click the policy name
    let source_data = "Source: " + source['filename'] + ":" + source['lineNumber']
    // append the optional message if any
    if (source['message'] && source['message'].length > 0)
        source_data += ", message=" + source['message']

    // set up an onclick handler for the policy name to show the source_data text,
    // and pass the CSS class as the 3rd parameter set the colours
    display('BOT[<a onclick="alert(\'' + source_data + '\')">' + policy + '</a>]', myJson['speechText'], 'pol_' + policy)

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

        if (format === 'text_image' || format === 'summary' || format === "farewell") {
            let image_path = 'https://oat-2-data.s3.amazonaws.com/images/multi_domain_default.jpg'
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
                    descriptionNode.innerHTML = image_list[i]['title']
                }

                if (image_list.length < 3) {
                    for (let i = image_list.length, len = 3; i < len; i++) {
                        image_box = document.getElementById('img' + i)
                        image_box.remove()
                    }
                }
            }
        }

        if (format === "grid_list") {
            if (image_list.length > 0) {
                for (let i = 0, len = image_list.length; i < len; i++) {
                    image_box = document.getElementById('img' + i)
                    imageNode = image_box.querySelector('img')
                    console.log(imageNode)
                    imageNode.setAttribute('src', image_list[i]['path'])
                    imageNode.addEventListener('click', function() {
                        document.getElementById('inputText').value = screen_interaction['onClickList'][i];
                        call();
                    })
                }
            }

            if (image_list.length < 9) {
                for (let i = image_list.length, len = 9; i < len; i++) {
                    image_box = document.getElementById('img' + i)
                    image_box.remove()
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

    let video_display_link;
    if (format === "video" && "video" in screen_interaction) {
        const video_obj = screen_interaction['video']
        const video_path = video_obj['hostedMp4']
        if (video_obj.hasOwnProperty('startTime') && video_obj.hasOwnProperty('endTime')) {
            video_display_link = `${video_path}#t=${video_obj['startTime']},${video_obj['endTime']}`;
        } else {
            video_display_link = video_path;
        }
        document.getElementById('video').firstElementChild.setAttribute('src', video_display_link)
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

const display = (user, text, cls=null) => {
    chatNode = document.getElementsByClassName("chat")[0]
    chatNode.innerHTML += "<p class=\"" + cls + "\"> <strong>" + user + "</strong>: " + text + "</p>";
    chatNode.scrollTop= chatNode.scrollHeight
}

const assignID = () => {
    var id = Math.floor(Math.random() * Date.now()).toString(16)
    document.getElementById("IDField").value = "local_" + id
}
