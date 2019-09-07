var fs = require('fs');


fs.readFile("build/index.html", 'utf8', function (err, contents) {
    if (err) {
        return console.error(err);
    }
    contents = contents.replace(/<ssihead\s?\/>/gi, "<!--#include virtual=\"/bootstraphead.html\"-->");
    contents = contents.replace(/<ssibodytop\s?\/>/gi, "<!--#include virtual=\"/navbar.html\"-->");
    contents = contents.replace(/<ssibodybottom\s?\/>/gi, "<!--#include virtual=\"/endOfBody.html\"-->");

    fs.writeFile("build/index.html", contents, 'utf8', function (err) {
        if (err) {
            return console.error(err);
        }
        fs.chmod("build/index.html", 0o775, function (err) {
            if (err) {
                return console.error(err);
            }
        });
    });
});
