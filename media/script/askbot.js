/**
 *
 * This is a modified widget from askbot to prevent loading all it's resources
 */
$(function() {
  var AskbotAskWidget1;
  function load() {
    var link = document.createElement('link');
    var protocol = document.location.protocol;

    link.setAttribute("rel", "stylesheet");
    link.setAttribute("href", protocol + '//help.mapstory.org/widgets/ask/1.css');

    //creating the div
    var motherDiv = document.createElement('div');
    motherDiv.setAttribute("id", "AskbotAskWidget1");

    var containerDiv = document.createElement('div');
    motherDiv.appendChild(containerDiv);

    var closeButton = document.createElement('a');
    closeButton.setAttribute('href', '#');
    closeButton.setAttribute('id', 'AskbotModalClose');
    $(closeButton).click(function() {
          $("#AskbotAskWidget1").css('visibility','hidden');
    });
    closeButton.innerHTML= 'Close';

    containerDiv.appendChild(closeButton);

    var iframe = document.createElement('iframe');
    iframe.setAttribute('src', protocol + '//help.mapstory.org/widgets/ask/1/');

    containerDiv.appendChild(iframe);

    var body = document.getElementsByTagName('body')[0];
    if (body){
      body.appendChild(link);
      body.appendChild(motherDiv);
    }
  }
  function show(ev) {
      ev.preventDefault();
      var widget = $("#AskbotAskWidget1");
      if (widget.find('iframe').length === 0) {
          load();
          widget = $(widget.selector);
      }
      widget.css('visibility','visible');
      widget.find('iframe').focus();
  }
  AskbotAskWidget1 = $("#AskbotAskButton").click(show);
});