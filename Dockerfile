FROM <claude-sandbox-base>
RUN apt-get update && apt-get install -y nodejs npm
RUN npm install -g get-shit-done-cc
