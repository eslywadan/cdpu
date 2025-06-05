function copyToClipboard(textToCopy) {
  // navigator clipboard api needs a secure context (https)
  if (navigator.clipboard && window.isSecureContext) {
      // navigator clipboard api method'
      return navigator.clipboard.writeText(textToCopy);
  } else {
      // text area method
      let textArea = document.createElement("textarea");
      textArea.value = textToCopy;
      // make the textarea out of viewport
      textArea.style.position = "fixed";
      textArea.style.left = "-999999px";
      textArea.style.top = "-999999px";
      document.body.appendChild(textArea);
      textArea.focus();
      textArea.select();
      return new Promise((res, rej) => {
          // here the magic happens
          document.execCommand('copy') ? res() : rej();
          textArea.remove();
      });
  }
}

function cpApiKey() {
  /* Get the text field */
  var copyText = document.getElementById("txt_apikey");
  /*print(copyText)

  /* Select the text field */
  copyText.select();
  textToCopy = copyText.setSelectionRange(0, 99999); /* For mobile devices */

  /* Copy the text inside the text field */
  /* navigator.clipboard.writeText(copyText.value); */
  copyToClipboard(textToCopy)
  /* Alert the copied text */
  alert("Copied the text: " + textToCopy);
}
