curl -s https://api.github.com/repos/temper-mc/temper/releases/latest \
  | jq -r '.tag_name' \
  | sed 's/^v//'
