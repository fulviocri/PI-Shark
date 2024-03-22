alias cls='clear'

alias ll='ls -lah --color=auto'
alias mkdir='mkdir -p'
alias rm='rm -i'
alias cp='cp -i'
alias mv='mv -i'
alias ..='cd ..'
alias ...='cd ../..'
alias cd..='cd ..'
alias mount='mount | column -t'
alias df='df -h'
alias du='du -h'

alias chown='chown --preserve-root'
alias chmod='chmod --preserve-root'
alias chgrp='chgrp --preserve-root'

alias grep='grep --color=auto -i'
alias fgrep='fgrep --color=auto'
alias egrep='egrep --color=auto'

alias free='free -h'

alias meminfo='free -m -l -t'
alias psmem='ps auxf | sort -nr -k 4'
alias psmem10='ps auxf | sort -nr -k 4 | head -10'

alias pscpu='ps auxf | sort -nr -k 3'
alias pscpu10='ps auxf | sort -nr -k 3 | head -10'

alias cpuinfo='lscpu'

alias h='history | nl'
alias j='jobs -l'

alias path='echo -e ${PATH//:/\\n}'
alias now='date +"%T"'
alias nowtime=now
alias nowdate='date +"%d-%m-%Y"'

alias ping='ping -c 5'
alias fastping='ping -c 100 -s.2'
alias ports='netstat -tulanp'

alias wget='wget -c'

alias update='apt-get update && apt-get upgrade'

alias grepip='cat /var/lib/misc/dnsmasq.leases | grep -oE "\b([0-9]{1,3}\.){3}[0-9]{1,3}\b"'
alias wanip='curl -s http://whatismyip.akamai.com/'