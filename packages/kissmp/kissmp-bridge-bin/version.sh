curl -s https://api.github.com/repos/TheHellBox/KISS-multiplayer/releases/latest \
  | jq -r '.tag_name' \
  | sed 's/^v//'
