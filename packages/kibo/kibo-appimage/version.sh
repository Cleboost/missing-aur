curl -s https://www.kiboanime.app/ \
  | grep -oP 'v\K[0-9]+\.[0-9]+\.[0-9]+' \
  | head -n1