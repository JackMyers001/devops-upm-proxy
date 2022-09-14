# devops-upm-proxy

Proxy for Unity packages stored in DevOps

## About

### Background

Unity has used NPM as it's package manager since 2018.2. NPM is *usually* used for serving Node packages (it is called the "Node Package Manager" for a reason), however there's really no reason why it can't be used by other services; all it needs to do is track versions of packages and their required dependencies.

Presumably, Unity used NPM as it was already widespread and most Git services (GitHub, GitLab, DevOps etc.) already had built-in NPM registries. This would make it easy for end users to start pushing their packages (which are likely already on Git) through their Git service.

### The problem

You probably already know the problem if you've stumbled upon this repo: Unity is unable to list not-installed packages that are on a DevOps NPM registry.

It *can* show information about packages that it *does* know about (including full package install + upgrade), however the only way to inform Unity about a package is by editing a Unity project's `Packages/manifest.json`, which will then go and install it. Not particularly helpful.

So why can't Unity get a list of all the packages on DevOps NPM? As with most things in tech, it's Microsoft's fault.

NPM has two ways of getting a list of packages.

The first (and older?) method is a "get all packages" endpoint (e.g. `registry.example.com/-/all`). Most registries (like `npmjs.com`) no longer have this endpoint, as it's... inefficient. `registry.npmjs.com/-/all`, for example, used to return all packages, but now just returns an empty JSON repsonse. The reason is pretty obvious; `npmjs.com` has over 1.3 million *public* packages.

The other method is to search for packages. In Unity's case, it will search for packages based on the `scopes` set in `Packages/manifest.json` (i.e. `registry.example.com/-/v1/search?text=com.example&from=0&size=250`).

Unity will try the search method first, and if that fails, it will fallback to trying to get all packages. So why can't Unity find packages on a DevOps NPM registry? Because Microsoft hasn't implemented ***either*** endpoint!

### The Solution

The way this script works is pretty simple. There are two small programs; one is a "scraper" program which periodically queries the DevOps Artifact feed API + DevOps NPM API for info about all packages, and saves the "metadata" to a MongoDB database. The other program is a web server that implements the bare minimum NPM API, and pulls data from said the Mongo database to answer client queries.

Clients still authenticate with the DevOps NPM registry to actually download the packages; only the "metadata" is stored in the database.

It's truly terrible, but it *does* work.

## Running

I recommend running all three services (scraper, proxy and Mongo) in Docker. `Dockerfile`s and an example `docker-compose.yml` can be used as a starting point.

If you do decide to run outside of Docker, the minimum requirements are:

- Python 3.10 (or later?)
- Pip packages installed (see `requirements.txt` in `proxy/` and `scraper/`)
- MongoDB *with authentication enabled*

There are also a bunch of required and optional environmental variables that must be set.

### Scraper environmental variables

| Name            | Description | Default Value? |
| --------------- | ----------- | -------------- |
| ORG_NAME        | DevOps org name (i.e. `https://dev.azure.com/<OrgName>`) | Required 
| FEED_ID         | DevOps Artifact feed name | Required |
| PAT             | DevOps Personal Access token. Required scopes: Build -> Read, Packaging -> Read | Required |
| FALLBACK_AUTHOR | Package author name that will appear in Unity if no author is specified. Recommended to be your company's name | Required |
| REFRESH         | How often the scraper should check for new packages (in seconds). Recommended is 900 | 900 |
| MONGO_HOST      | MongoDB host (if using Docker, likely the name of the container) | Required |
| MONGO_PORT      | MongoDB port | 27017 |
| MONGO_USER      | MongoDB username | Required |
| MONGO_PASS      | MongoDB password | Required |
| MONGO_DB        | Mongo database | Required |
| WIPE_DB | (Optional) If set (to any value), MongoDB will be wiped on start | False |

### Proxy environmental variables

| Name            | Description | Default Value? |
| --------------- | ----------- | -------------- | 
| MONGO_HOST      | MongoDB host (if using Docker, likely the name of the container) | Required |
| MONGO_PORT      | MongoDB port | 27017 |
| MONGO_USER      | MongoDB username | Required |
| MONGO_PASS      | MongoDB password | Required |
| MONGO_DB        | Mongo database | Required |

# License

Licensed under GPLv3. If you do make improvements, I would ask that you do try to upstream your changes if possible. This is quick and dirty code, so any improvements would be appreciated :D.
