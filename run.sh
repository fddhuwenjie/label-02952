#!/usr/bin/env bash
set -euo pipefail

# ============================================================
#  拼音输入法引擎 - 一键构建 & 验证脚本
#  兼容 macOS / Linux / Windows (Git Bash / MSYS2 / WSL)
# ============================================================

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

info()  { printf "${CYAN}[INFO]${NC}  %s\n" "$*"; }
ok()    { printf "${GREEN}[OK]${NC}    %s\n" "$*"; }
warn()  { printf "${YELLOW}[WARN]${NC}  %s\n" "$*"; }
fail()  { printf "${RED}[FAIL]${NC}  %s\n" "$*"; }

PASS=0
FAIL=0

check_result() {
  local label="$1" output="$2" expect="$3"
  if echo "$output" | grep -q "$expect"; then
    ok "$label"
    PASS=$((PASS + 1))
  else
    fail "$label (期望包含: $expect)"
    echo "    实际输出: $output"
    FAIL=$((FAIL + 1))
  fi
}

# ---------- 检测操作系统 ----------
detect_os() {
  case "$(uname -s 2>/dev/null || echo Windows)" in
    Darwin*)  echo "mac"   ;;
    Linux*)   echo "linux" ;;
    MINGW*|MSYS*|CYGWIN*|Windows*) echo "windows" ;;
    *)        echo "linux" ;;
  esac
}

OS=$(detect_os)
info "检测到系统: $OS"

# ---------- 安装 Docker ----------
install_docker() {
  info "未检测到 Docker，尝试自动安装..."
  case "$OS" in
    mac)
      if command -v brew &>/dev/null; then
        info "通过 Homebrew 安装 Docker Desktop..."
        brew install --cask docker
        info "请手动启动 Docker Desktop 应用，等待其完全启动后重新运行此脚本"
        exit 1
      else
        fail "未找到 Homebrew，请先安装: https://brew.sh"
        fail "或手动安装 Docker Desktop: https://www.docker.com/products/docker-desktop"
        exit 1
      fi
      ;;
    linux)
      if command -v apt-get &>/dev/null; then
        info "通过 apt 安装 Docker..."
        sudo apt-get update
        sudo apt-get install -y docker.io docker-compose-plugin
        sudo systemctl start docker
        sudo usermod -aG docker "$USER"
        warn "已将当前用户加入 docker 组，如遇权限问题请重新登录"
      elif command -v yum &>/dev/null; then
        info "通过 yum 安装 Docker..."
        sudo yum install -y docker docker-compose-plugin
        sudo systemctl start docker
        sudo usermod -aG docker "$USER"
      elif command -v pacman &>/dev/null; then
        info "通过 pacman 安装 Docker..."
        sudo pacman -Sy --noconfirm docker docker-compose
        sudo systemctl start docker
        sudo usermod -aG docker "$USER"
      else
        fail "无法识别包管理器，请手动安装 Docker: https://docs.docker.com/engine/install/"
        exit 1
      fi
      ;;
    windows)
      if command -v choco &>/dev/null; then
        info "通过 Chocolatey 安装 Docker Desktop..."
        choco install docker-desktop -y
        info "请手动启动 Docker Desktop，等待其完全启动后重新运行此脚本"
        exit 1
      elif command -v winget &>/dev/null; then
        info "通过 winget 安装 Docker Desktop..."
        winget install -e --id Docker.DockerDesktop
        info "请手动启动 Docker Desktop，等待其完全启动后重新运行此脚本"
        exit 1
      else
        fail "请手动安装 Docker Desktop: https://www.docker.com/products/docker-desktop"
        exit 1
      fi
      ;;
  esac
}

# ---------- 检测 Docker Compose 命令 ----------
detect_compose() {
  if docker compose version &>/dev/null 2>&1; then
    echo "docker compose"
  elif command -v docker-compose &>/dev/null 2>&1; then
    echo "docker-compose"
  else
    echo ""
  fi
}

# ---------- 前置检查 ----------
if ! command -v docker &>/dev/null; then
  install_docker
fi

# 检查 Docker 守护进程是否运行
if ! docker info &>/dev/null 2>&1; then
  warn "Docker 已安装但守护进程未运行"
  case "$OS" in
    mac)
      info "尝试启动 Docker Desktop..."
      open -a Docker 2>/dev/null || true
      ;;
    linux)
      info "尝试启动 Docker 服务..."
      sudo systemctl start docker 2>/dev/null || true
      ;;
    windows)
      info "请手动启动 Docker Desktop"
      ;;
  esac
  info "等待 Docker 启动..."
  for i in $(seq 1 30); do
    if docker info &>/dev/null 2>&1; then
      break
    fi
    sleep 2
    printf "."
  done
  echo ""
  if ! docker info &>/dev/null 2>&1; then
    fail "Docker 守护进程启动超时，请手动启动后重试"
    exit 1
  fi
fi
ok "Docker 已就绪"

COMPOSE_CMD=$(detect_compose)
if [ -z "$COMPOSE_CMD" ]; then
  fail "未找到 docker compose，请升级 Docker 或安装 docker-compose"
  exit 1
fi
ok "Compose 命令: $COMPOSE_CMD"

# ---------- 构建 & 启动 ----------
info "构建并启动容器..."
$COMPOSE_CMD up -d --build

# 等待容器就绪
info "等待容器启动..."
sleep 3

CONTAINER="pinyin-input-method"

if ! docker ps --format '{{.Names}}' | grep -q "^${CONTAINER}$"; then
  fail "容器 $CONTAINER 未正常运行"
  docker logs "$CONTAINER" 2>&1 | tail -20
  exit 1
fi
ok "容器 $CONTAINER 已运行"

# ---------- 验证测试 ----------
echo ""
info "========== 开始验证测试 =========="
echo ""

# 1) 单拼音查询
info "测试 1: 单拼音查询 (ni)"
OUT=$(docker exec "$CONTAINER" python -m app query ni 2>&1)
check_result "单拼音 'ni' 返回候选字 '你'" "$OUT" '"你"'

# 2) 连续拼音 - 双音节
info "测试 2: 连续拼音 (nihao)"
OUT=$(docker exec "$CONTAINER" python -m app query nihao 2>&1)
check_result "连续拼音 'nihao' 正确切分" "$OUT" '"ni"'
check_result "连续拼音 'nihao' 包含 'hao'" "$OUT" '"hao"'
check_result "连续拼音 'nihao' 返回 '你'" "$OUT" '"你"'
check_result "连续拼音 'nihao' 返回 '好'" "$OUT" '"好"'

# 3) 连续拼音 - 多音节
info "测试 3: 长连续拼音 (woaibeijing)"
OUT=$(docker exec "$CONTAINER" python -m app query woaibeijing 2>&1)
check_result "长拼音 'woaibeijing' 切分出 'wo'" "$OUT" '"wo"'
check_result "长拼音 'woaibeijing' 切分出 'ai'" "$OUT" '"ai"'
check_result "长拼音 'woaibeijing' 切分出 'bei'" "$OUT" '"bei"'
check_result "长拼音 'woaibeijing' 切分出 'jing'" "$OUT" '"jing"'
check_result "长拼音 'woaibeijing' 返回 '我'" "$OUT" '"我"'
check_result "长拼音 'woaibeijing' 返回 '爱'" "$OUT" '"爱"'
check_result "长拼音 'woaibeijing' 返回 '北'" "$OUT" '"北"'
check_result "长拼音 'woaibeijing' 返回 '京'" "$OUT" '"京"'

# 4) 空格分词转换
info "测试 4: 空格分词转换 (ni hao shi jie)"
OUT=$(docker exec "$CONTAINER" python -m app convert ni hao shi jie 2>&1)
check_result "convert 返回 '你'" "$OUT" '"你"'
check_result "convert 返回 '好'" "$OUT" '"好"'
check_result "convert 返回 '是'" "$OUT" '"是"'
check_result "convert 返回 '就'" "$OUT" '"就"'

# 5) 拼音搜索
info "测试 5: 拼音搜索 (zh)"
OUT=$(docker exec "$CONTAINER" python -m app search zh 2>&1)
check_result "搜索 'zh' 包含 'zhong'" "$OUT" '"zhong"'
check_result "搜索 'zh' 包含 'zhi'" "$OUT" '"zhi"'

# 6) 无效输入
info "测试 6: 无效拼音 (xyz)"
OUT=$(docker exec "$CONTAINER" python -m app query xyz 2>&1)
check_result "无效拼音返回空候选" "$OUT" '"count": 0'

# 7) 列出所有拼音
info "测试 7: 列出所有拼音"
OUT=$(docker exec "$CONTAINER" python -m app query zhongguo 2>&1)
check_result "连续拼音 'zhongguo' 返回 '中'" "$OUT" '"中"'
check_result "连续拼音 'zhongguo' 返回 '国'" "$OUT" '"国"'

# ---------- 结果汇总 ----------
echo ""
info "========== 测试结果 =========="
ok "通过: $PASS"
if [ "$FAIL" -gt 0 ]; then
  fail "失败: $FAIL"
  echo ""
  fail "部分测试未通过，请检查上方输出"
  exit 1
else
  echo ""
  ok "全部测试通过 ✅"
fi
