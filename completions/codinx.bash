# bash completion untuk CodinX — pasang: cp completions/codinx.bash /etc/bash_completion.d/codinx
_codinx() {
  local cur prev cmds
  cur="${COMP_WORDS[COMP_CWORD]}"; prev="${COMP_WORDS[COMP_CWORD-1]}"
  cmds="run connect doctor models sessions logs"
  case "$prev" in
    codinx) COMPREPLY=( $(compgen -W "$cmds --version --model --no-color" -- "$cur") ); return ;;
    run)    COMPREPLY=( $(compgen -W "--continue --auto --plan --format --model --no-probe --no-color" -- "$cur") ); return ;;
    --format) COMPREPLY=( $(compgen -W "text json" -- "$cur") ); return ;;
  esac
}
complete -F _codinx codinx
