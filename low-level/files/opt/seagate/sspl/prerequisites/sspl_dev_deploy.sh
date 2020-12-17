#!/bin/bash
#
# Copyright (c) 2020 Seagate Technology LLC and/or its Affiliates
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.
# For any questions about this software or licensing,
# please email opensource@seagate.com or cortx-questions@seagate.com.
#


# *******************************************************************
#  Description:   SSPL prerequisites script to setup environment
#  Purpose    :   Setup yum repos, consul and rabbitmq for SSPL
#  Usage      :   ./sspl_dev_deploy.sh --help
# *******************************************************************


set -eE

LOG_FILE="${LOG_FILE:-/var/log/cortx/sspl/sspl-prereqs.log}"
export LOG_FILE

if [[ ! -e "$LOG_FILE" ]]; then
    mkdir -p $(dirname "${LOG_FILE}")
fi

# Config file to store cluster_id & node_id
CONFIG_FILE="/opt/seagate/cortx/sspl/generated_configs"
if [[ ! -e "$CONFIG_FILE" ]]; then
    mkdir -p $(dirname "$CONFIG_FILE")
    touch $CONFIG_FILE
fi

echo "INFO: ******** Running $0  ********" 2>&1 | tee -a "${LOG_FILE}"
echo "INFO: Date: $(date)" 2>&1 | tee -a "${LOG_FILE}"

do_cleanup=false
install_3rd_party_packages=false
disable_sub_mgr=false
TARGET_BUILD=
COMPONENT="SSPL"
PRODUCT_VERSION="LDR_R2"
NODE="srvnode-1"
RMQ_USER="sspluser"
CNTRLR_A="10.0.0.2"
CNTRLR_B="10.0.0.3"
CNTRLR_A_PORT="80"
CNTRLR_B_PORT="80"
CNTRLR_USER=
CNTRLR_PASSWD=
BMC_IP=
BMC_USER=
BMC_PASSWD=


usage()
{
    echo "\
    SSPL prerequisite script.
    (Bounded to single node provisioning)

    Usage:
         $0
            [-V|--product_version  <LDR_R1, LDR_R2>]
            [-N|--node  <Node name/id>]
            [-A|--cntrlr_a  <controller A IP>]
            [-B|--cntrlr_b  <controller B IP>]
            [-T|--target_build_url  <target build url>]
            [--Ap|--cntrlr_a_port  <controller A Port>]
            [--Bp|--cntrlr_b_port  <controller B Port>]
            [-U|--cntrlr_user   <username>]
            [-P|--cntrlr_pass   <password>]
            [--i|--bmc_ip     <bmc ipv4 address>]
            [--u|--bmc_user   <bmc user>]
            [--p|--bmc_passwd <bmc password>]
            [--Ru|--rmq_user    <rabbitmq username>]
            [--Rp|--rmq_passwd  <rabbitmq password>]
            [-D|--disable-sub-mgr]
            [--standalone-installation]
            [--cleanup]
            [-h|--help]

    OPTION:
    -V      <PRODUCT VERSION>   Product version (LDR_R1 | LDR_R2)
    -N      <NODE NAME>         Default 'srvnode-1'
    -A      <IP ADDRESS>        IP address of controller A (default 10.0.0.2)
    -B      <IP ADDRESS>        IP address of controller B (default 10.0.0.3)
    --Ap    <CNTRLR A PORT>     Controller A port (default 80)
    --Bp    <CNTRLR A PORT>     Controller B port (default 80)
    -U      <USER NAME>         Username for controller
    -P      <PASSWORD>          Password for controller (Encrypted)
    --Ru    <RMQ USER>          User for Rabbitmq (Encrypted)
    --Rp    <RMQ PASSWORD>      Password for Rabbitmq (Encrypted)
    --i     <BMC IP>            BMC IPV4 for Node-1
    --u     <BMC USER>          BMC User for Node-1
    --p     <BMC PASSWORD>      BMC Password for Node-1 (Encrypted)
    -T      <TARGET BUILD>      Target build base url pointed to release bundle base directory,
                if specified the following directory structure is assumed:
                <base_url>/
                    rhel7.7 or centos7.7   <- OS ISO is mounted here
                    3rd_party              <- CORTX 3rd party ISO is mounted here
                    cortx_iso              <- CORTX ISO (main) is mounted here
    --standalone_installation   Configure SSPL 3rd party dependencies like consul, rabbitmq
    -D|--disable-sub-mgr        For RHEL. To install prerequisites by disabling
                                subscription manager (usually, not recommended).
                                If this option is not provided it is expected that
                                either the system is not RHEL or system is already
                                registered with subscription manager
    --cleanup                   Remove dependencies
    "
    exit 0
}

parse_args()
{
    while [[ $# -gt 0 ]]; do
        case "$1" in
        -h|--help)
            usage ;;
        --cleanup)
            do_cleanup=true
            shift ;;
        -D|--disable-sub-mgr)
            disable_sub_mgr=true
            shift ;;
        --standalone-installation)
            install_3rd_party_packages=true
            shift ;;
        -V|--product_version)
            [ -z "$2" ] && echo "ERROR: Product version(LDR_R1/LDR_R2) not provided" && exit 1;
            PRODUCT_VERSION="$2"
            shift 2 ;;
        -N|--node)
            [ -z "$2" ] && echo "ERROR: Node name not provided" && exit 1;
            NODE="$2"
            shift 2 ;;
        --Ru|--rmq_user)
            [ -z "$2" ] && echo "ERROR: Rabbitmq user not provided" && exit 1;
            RMQ_USER="$2"
            shift 2 ;;
        --Rp|--rmq_passwd)
            [ -z "$2" ] && echo "ERROR: Rabbitmq password not provided" && exit 1;
            RMQ_PASSWD="$2"
            shift 2 ;;
        -A|--cntrlr_a)
            [ -z "$2" ] && echo "ERROR: Controller A IP not provided" && exit 1;
            CNTRLR_A="$2"
            shift 2 ;;
        --Ap|--cntrlr_a_port)
            [ -z "$2" ] && echo "ERROR: Controller A Port not provided" && exit 1;
            CNTRLR_A_PORT="$2"
            shift 2 ;;
        -B|--cntrlr_b)
            [ -z "$2" ] && echo "ERROR: Controller B IP not provided" && exit 1;
            CNTRLR_B="$2"
            shift 2 ;;
        --Bp|--cntrlr_b_port)
            [ -z "$2" ] && echo "ERROR: Controller B Port not provided" && exit 1;
            CNTRLR_B_PORT="$2"
            shift 2 ;;
        -U|--cntrlr_user)
            [ -z "$2" ] && echo "ERROR: Controller user name not provided" && exit 1;
            CNTRLR_USER="$2"
            shift 2 ;;
        -P|--cntrlr_pass)
            [ -z "$2" ] && echo "ERROR: Controller password not provided" && exit 1;
            CNTRLR_PASSWD="$2"
            shift 2 ;;
        -T|--target_build_url)
            [ -z "$2" ] && echo "ERROR: Target build not provided" && exit 1;
            TARGET_BUILD="$2"
            shift 2 ;;
        --i|--bmc_ip)
            [ -z "$2" ] && echo "ERROR: BMC IP not provided" && exit 1;
            BMC_IP="$2"
            shift 2 ;;
        --u|--bmc_user)
            [ -z "$2" ] && echo "ERROR: BMC user not provided" && exit 1;
            BMC_USER="$2"
            shift 2 ;;
        --p|--bmc_passwd)
            [ -z "$2" ] && echo "ERROR: BMC password not provided" && exit 1;
            BMC_PASSWD="$2"
            shift 2 ;;
        *)
            echo "ERROR: Unknown option provided: $1"
            exit 1 ;;
        esac
    done
}

parse_args "$@"

# Check for required arguments
[ -z "$CNTRLR_USER" ] && echo "ERROR: -U <controller user name> is required." && exit 1;
[ -z "$CNTRLR_PASSWD" ] && echo "ERROR: -P <controller password> is required." && exit 1;
[ "$PRODUCT_VERSION" == "LDR_R2" ] && {
    echo "Skipping BMC information for LDR_R2..." 2>&1 | tee -a "${LOG_FILE}" ;
    }|| {
    [ -z "$BMC_IP" ] && echo "ERROR: --i <BMC IPV4> is required." && exit 1;
    [ -z "$BMC_USER" ] && echo "ERROR: --u <BMC user> is required." && exit 1;
    [ -z "$BMC_PASSWD" ] && echo "ERROR: --p <BMC password> is required." && exit 1;
}

# Cleanup
cleanup(){
    systemctl stop rabbitmq-server
    yum remove -y consul rabbitmq-server cortx-utils
    yum remove -y cortx-sspl.noarch
}
[ "$do_cleanup" == "true" ] && cleanup

# Setup common & 3rd_party repos
CORTX_MONITOR_BASE_URL="https://raw.githubusercontent.com/mariyappanp/cortx-monitor/EOS-15396_self_prv/low-level/files/opt/seagate/sspl"
curl $CORTX_MONITOR_BASE_URL/prerequisites/setup_yum_repos.sh -o setup_yum_repos.sh
chmod a+x setup_yum_repos.sh

if [ "$disable_sub_mgr" == "true" ] && [ -n "$TARGET_BUILD" ]; then
    ./setup_yum_repos.sh -d -t $TARGET_BUILD 2>&1 | tee -a "${LOG_FILE}"
elif [ "$disable_sub_mgr" == "true" ]; then
    ./setup_yum_repos.sh -d 2>&1 | tee -a "${LOG_FILE}"
elif [ -n "$TARGET_BUILD" ]; then
    ./setup_yum_repos.sh -t $TARGET_BUILD 2>&1 | tee -a "${LOG_FILE}"
else
    ./setup_yum_repos.sh 2>&1 | tee -a "${LOG_FILE}"
fi

echo -e "\nDone setup repos" 2>&1 | tee -a "${LOG_FILE}"


# Install prereq script dependencies
yum install -y python3
pip3 install configobj

# Install required RPMS if not available
"$install_3rd_party_packages" && {
    rpm -qa | grep "cortx-py-utils" || {
        echo "INFO: INSTALLING cortx-py-utils..." 2>&1 | tee -a "${LOG_FILE}"
        yum install -y cortx-py-utils 2>&1 | tee -a "${LOG_FILE}"
    }
    rpm -qa | grep "consul" || {
        echo "INFO: INSTALLING consul..." 2>&1 | tee -a "${LOG_FILE}"
        yum install -y consul 2>&1 | tee -a "${LOG_FILE}"
    }
    rpm -qa | grep "rabbitmq-server" || {
        echo "INFO: INSTALLING rabbitmq-server..." 2>&1 | tee -a "${LOG_FILE}"
        yum install -y rabbitmq-server 2>&1 | tee -a "${LOG_FILE}"
    }
}


setup_consul(){
    if ! [ -x "$(command -v consul)" ]; then
        echo "ERROR: Consul is not available. \
        For consul and other 3rd party package installation, \
        check prereq script usage. Exiting."
        exit 1
    fi
    # Create config file for consul agent
    CONSUL_CONFIG_DIR='/opt/seagate/cortx/sspl/bin'
    CONSUL_CONFIG_FILE="$CONSUL_CONFIG_DIR/consul_config.json"
    if [[ ! -e "$CONSUL_CONFIG_DIR" ]]; then
        mkdir -p $(dirname "${CONSUL_CONFIG_DIR}")
    fi
    cat << EOF >> $CONSUL_CONFIG_FILE
        {
            "watches": [
                {
                    "type": "key",
                    "key": "sspl/config/SYSTEM_INFORMATION/log_level",
                    "args": ["/opt/seagate/cortx/sspl/bin/consume_cfg_change_alert"]
                }
            ]
        }
EOF
    # Invoke consul agent from fallback path
    CONSUL_PS=$(pgrep "consul" || true)
    [ -z "$CONSUL_PS" ] &&
        consul agent -dev -config-file=$CONSUL_CONFIG_FILE &>/dev/null &

    TRIES=0
    while [ -z "$CONSUL_PS" ]; do
        sleep 2
        TRIES=$((TRIES+1))
        CONSUL_PS=$(pgrep "consul" || true)
        if [ $TRIES -gt 5 ]; then
            echo "ERROR: Consul service is not started"
            break
        fi
    done

    # Choose sspl.conf file based on component version
    SSPL_CONF='/etc/sspl.conf'
    curl $CORTX_MONITOR_BASE_URL/conf/sspl.conf.${PRODUCT_VERSION} -o sspl.conf;
    mv sspl.conf $SSPL_CONF

    # Load sspl conf to consul
    curl $CORTX_MONITOR_BASE_URL/prerequisites/common_config_SN.ini -o common_config_SN.ini;
    curl $CORTX_MONITOR_BASE_URL/prerequisites/feed_sspl_conf_to_consul.py -o feed_sspl_conf_to_consul.py;
    chmod a+x feed_sspl_conf_to_consul.py

    # Update persistent cluster_id and node_id in common config if not already present
    [ -z "$(consul kv get system_information/cluster_id)" ] && {
        cluster_id=$(sed -nr 's/^cluster_id=([^,]+)$/\1/p' $CONFIG_FILE | head -1)
        [ -z "$cluster_id" ] && cluster_id=$(uuidgen)
        consul kv put system_information/cluster_id "$cluster_id"
    } || {
        cluster_id=$(consul kv get system_information/cluster_id)
    }

    # Update persistent node_id in common config if not already present
    [ -z "$(consul kv get system_information/$NODE/node_id)" ] && {
        node_id=$(sed -nr 's/^node_id=([^,]+)$/\1/p' $CONFIG_FILE | head -1)
        [ -z "$node_id" ] && node_id=$(uuidgen)
        [ -z $NODE ] && NODE="srvnode-1"
        consul kv put system_information/$NODE/node_id "$node_id"
    } || {
        node_id=$(consul kv get system_information/$NODE/node_id)
    }

    # Update CONFIG_FILE wih identified cluster_id & node_id
    echo -e "cluster_id=$cluster_id\nnode_id=$node_id" > "$CONFIG_FILE"

    echo "INFO: Inserting common config in consul.."
    [ "$PRODUCT_VERSION" == "LDR_R2" ] && {
        python3 feed_sspl_conf_to_consul.py -F common_config_SN.ini -N $NODE \
                    -A $CNTRLR_A -B $CNTRLR_B -U $CNTRLR_USER -P $CNTRLR_PASSWD \
                    -Ap $CNTRLR_A_PORT -Bp $CNTRLR_B_PORT ;
    } || {
        python3 feed_sspl_conf_to_consul.py -F common_config_SN.ini -N $NODE \
                    --bmc_ip $BMC_IP --bmc_user $BMC_USER --bmc_passwd $BMC_PASS \
                    -Ru $RMQ_USER -Rp $RMQ_PASSWD \
                    -A $CNTRLR_A -B $CNTRLR_B -U $CNTRLR_USER -P $CNTRLR_PASSWD \
                    -Ap $CNTRLR_A_PORT -Bp $CNTRLR_B_PORT ;
    }

    echo "INFO: Inserting $COMPONENT config in consul.."
    python3 feed_sspl_conf_to_consul.py -F $SSPL_CONF -N $NODE \
                    -C $COMPONENT -Ru $RMQ_USER -Rp $RMQ_PASSWD
    echo "Done consul setup."
}


setup_rabbitmq(){
    curl $CORTX_MONITOR_BASE_URL/prerequisites/sspl_rabbitmq_reinit -o sspl_rabbitmq_reinit;
    chmod a+x sspl_rabbitmq_reinit;
    python3 ./sspl_rabbitmq_reinit || {
        reinit_err="$?"
        echo -n "ERROR: sspl_rabbitmq_reinit failed "
        echo "with exit code ${reinit_err} for product $product"
        exit 1
    }
    echo "Done rabbitmq setup."
}

# Configure consul
setup_consul 2>&1 | tee -a "${LOG_FILE}"

# Configure rabbitmq-server
setup_rabbitmq 2>&1 | tee -a "${LOG_FILE}"

echo "For more details see: $LOG_FILE"
echo -e "\n***** SUCCESS!!! *****" 2>&1 | tee -a "${LOG_FILE}"
