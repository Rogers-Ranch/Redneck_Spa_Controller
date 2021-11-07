fetch('https://quotes.code-defined.com')
  .then(
    function(response) {
      if (response.status !== 200) {
        console.log('Looks like there was a problem. Status Code: ' +
          response.status);
        return;
      }
      
      // Examine the text in the response
      response.json().then(function(data) {
        // const quote = JSON.stringify(data["Item"]["quote"]);
        // const author = JSON.stringify(data["Item"]["author"]);
        const quote = JSON.stringify(data.Item["quote"]);
        const author = JSON.stringify(data.Item["author"]);
        document.getElementById("QOTD").innerHTML = quote;
        document.getElementById("Author").innerHTML = author.replaceAll('\"','');
      });
    }
  )
  .catch(function(err) {
    console.log('Fetch Error :-S', err);
  });