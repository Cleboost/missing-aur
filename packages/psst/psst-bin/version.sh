curl -s https://api.github.com/repos/jpochyla/psst/releases/tags/rolling \
  | jq -r '.name | split("(")[1] | split(")")[0] | gsub("-"; "_")'