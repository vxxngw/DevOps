# Personal Terraform scope and team integration

BaoLong owns the Jenkins VirtualBox Terraform root and cloud-cost estimate. Other members own Ansible and the two K3s VMs. Shared Ansible, observability and CI automation are preserved from main; do not delete them when merging this branch.

Use infra/terraform-virtualbox and scripts/invoke-jenkins-virtualbox.ps1 for the existing Jenkins VM. Keep runtime state, seed and keys outside Git. Never change the seed or recreate the existing VM to rerun cloud-init. Terraform lifecycle protection remains enabled.

The health timer helper scripts/configure-host.sh is optional and must run explicitly as root on Ubuntu. It does not install Jenkins, K3s or backup schedules. scripts/infra contains the team's existing Linux automation.

Historical Ansible source was backed up outside the repository during local experimentation; that experiment is not the team merge policy. Private Vaults and SSH keys remain untouched. No full-fleet acceptance is claimed.
