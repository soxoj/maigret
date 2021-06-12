# How to contribute

Hey! I'm really glad you're reading this. Maigret contains a lot of sites, and it is very hard to keep all the sites operational. That's why any fix is important. 

## How to add a new site

#### Beginner level

You can use Maigret **submit mode** (`maigret --submit URL`) to add a new site or update an existing site. In this mode Maigret do an automatic analysis of the given account URL or site main page URL to determine the site engine and methods to check account presence. After checking Maigret asks if you want to add the site, answering y/Y will rewrite the local database.

#### Advanced level

You can edit [the database JSON file](https://github.com/soxoj/maigret/blob/main/maigret/resources/data.json) (`./maigret/resources/data.json`) manually.

## Testing

There are CI checks for every PR to the Maigret repository. But it will be better to run `make format`, `make link` and `make test` to ensure you've made a corrent changes. 

## Submitting changes

To submit you changes you must [send a GitHub PR](https://github.com/soxoj/maigret/pulls) to the Maigret project.
Always write a clear log message for your commits. One-line messages are fine for small changes, but bigger changes should look like this:

    $ git commit -m "A brief summary of the commit
    > 
    > A paragraph describing what changed and its impact."

## Coding conventions

Start reading the code and you'll get the hang of it. ;)
