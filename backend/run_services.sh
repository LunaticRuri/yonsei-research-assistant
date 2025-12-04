#!/bin/bash

# 통합 서비스 운영 스크립트
# CLI, Strategy, Retrieval, Generation 서비스를 관리

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 스크립트 디렉토리 및 프로젝트 루트 설정
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# PID 파일 디렉토리
PID_DIR="$SCRIPT_DIR/pids"
mkdir -p "$PID_DIR"

# PID 파일 경로
CLI_PID_FILE="$PID_DIR/cli.pid"
STRATEGY_PID_FILE="$PID_DIR/strategy.pid"
RETRIEVAL_PID_FILE="$PID_DIR/retrieval.pid"
GENERATION_PID_FILE="$PID_DIR/generation.pid"

# 도움말 함수
show_help() {
    echo -e "${BLUE}사용법: $0 [옵션]${NC}"
    echo ""
    echo "옵션:"
    echo "  start [all|cli|strategy|retrieval|generation]   - 서비스 시작"
    echo "  stop [all|cli|strategy|retrieval|generation]    - 서비스 중지"
    echo "  restart [all|cli|strategy|retrieval|generation] - 서비스 재시작"
    echo "  status                                          - 서비스 상태 확인"
    echo "  help                                            - 도움말 표시"
}

# 프로세스 상태 확인 함수
check_status() {
    local pid_file=$1
    local name=$2
    
    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file")
        if ps -p "$pid" > /dev/null; then
            echo -e "${GREEN}$name 서비스가 실행 중입니다. (PID: $pid)${NC}"
            return 0
        else
            echo -e "${RED}$name 서비스가 실행 중이지 않지만 PID 파일이 존재합니다. (정리함)${NC}"
            rm "$pid_file"
            return 1
        fi
    else
        echo -e "${YELLOW}$name 서비스가 실행 중이지 않습니다.${NC}"
        return 1
    fi
}

# 서비스 시작 함수
start_service() {
    local service=$1
    
    cd "$PROJECT_ROOT" || exit

    case $service in
        "cli")
            if [ -f "$CLI_PID_FILE" ] && ps -p $(cat "$CLI_PID_FILE") > /dev/null; then
                echo -e "${YELLOW}CLI 서비스가 이미 실행 중입니다.${NC}"
            else
                echo -e "${BLUE}CLI 서비스 시작 중...${NC}"
                # 로그는 별도 처리되므로 /dev/null로 리다이렉트
                python3 -m backend.cli_interface.main > /dev/null 2>&1 &
                echo $! > "$CLI_PID_FILE"
                echo -e "${GREEN}CLI 서비스 시작됨 (PID: $(cat "$CLI_PID_FILE"))${NC}"
            fi
            ;;
        "strategy")
            if [ -f "$STRATEGY_PID_FILE" ] && ps -p $(cat "$STRATEGY_PID_FILE") > /dev/null; then
                echo -e "${YELLOW}Strategy 서비스가 이미 실행 중입니다.${NC}"
            else
                echo -e "${BLUE}Strategy 서비스 시작 중...${NC}"
                uvicorn backend.strategy_service.main:app --host 0.0.0.0 --port 8002 > /dev/null 2>&1 &
                echo $! > "$STRATEGY_PID_FILE"
                echo -e "${GREEN}Strategy 서비스 시작됨 (PID: $(cat "$STRATEGY_PID_FILE"))${NC}"
            fi
            ;;
        "retrieval")
            if [ -f "$RETRIEVAL_PID_FILE" ] && ps -p $(cat "$RETRIEVAL_PID_FILE") > /dev/null; then
                echo -e "${YELLOW}Retrieval 서비스가 이미 실행 중입니다.${NC}"
            else
                echo -e "${BLUE}Retrieval 서비스 시작 중...${NC}"
                uvicorn backend.retrieval_service.main:app --host 0.0.0.0 --port 8003 > /dev/null 2>&1 &
                echo $! > "$RETRIEVAL_PID_FILE"
                echo -e "${GREEN}Retrieval 서비스 시작됨 (PID: $(cat "$RETRIEVAL_PID_FILE"))${NC}"
            fi
            ;;
        "generation")
            if [ -f "$GENERATION_PID_FILE" ] && ps -p $(cat "$GENERATION_PID_FILE") > /dev/null; then
                echo -e "${YELLOW}Generation 서비스가 이미 실행 중입니다.${NC}"
            else
                echo -e "${BLUE}Generation 서비스 시작 중...${NC}"
                uvicorn backend.generation_service.main:app --host 0.0.0.0 --port 8004 > /dev/null 2>&1 &
                echo $! > "$GENERATION_PID_FILE"
                echo -e "${GREEN}Generation 서비스 시작됨 (PID: $(cat "$GENERATION_PID_FILE"))${NC}"
            fi
            ;;
        *)
            echo -e "${RED}알 수 없는 서비스: $service${NC}"
            ;;
    esac
}

# 서비스 중지 함수
stop_service() {
    local service=$1
    local pid_file=""
    
    case $service in
        "cli") pid_file="$CLI_PID_FILE" ;;
        "strategy") pid_file="$STRATEGY_PID_FILE" ;;
        "retrieval") pid_file="$RETRIEVAL_PID_FILE" ;;
        "generation") pid_file="$GENERATION_PID_FILE" ;;
        *) echo -e "${RED}알 수 없는 서비스: $service${NC}"; return ;;
    esac

    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file")
        echo -e "${BLUE}$service 서비스 중지 중... (PID: $pid)${NC}"
        kill "$pid" 2>/dev/null
        rm "$pid_file"
        echo -e "${GREEN}$service 서비스 중지됨${NC}"
    else
        echo -e "${YELLOW}$service 서비스가 실행 중이지 않습니다.${NC}"
    fi
}

# 메인 로직
case "$1" in
    start)
        if [ "$2" == "all" ] || [ -z "$2" ]; then
            start_service "strategy"
            start_service "retrieval"
            start_service "generation"
            start_service "cli"
        else
            start_service "$2"
        fi
        ;;
    stop)
        if [ "$2" == "all" ] || [ -z "$2" ]; then
            stop_service "cli"
            stop_service "generation"
            stop_service "retrieval"
            stop_service "strategy"
        else
            stop_service "$2"
        fi
        ;;
    restart)
        if [ "$2" == "all" ] || [ -z "$2" ]; then
            $0 stop all
            sleep 2
            $0 start all
        else
            $0 stop "$2"
            sleep 1
            $0 start "$2"
        fi
        ;;
    status)
        echo -e "${BLUE}=== 서비스 상태 ===${NC}"
        check_status "$CLI_PID_FILE" "CLI"
        check_status "$STRATEGY_PID_FILE" "Strategy"
        check_status "$RETRIEVAL_PID_FILE" "Retrieval"
        check_status "$GENERATION_PID_FILE" "Generation"
        ;;
    *)
        show_help
        exit 1
        ;;
esac

exit 0
