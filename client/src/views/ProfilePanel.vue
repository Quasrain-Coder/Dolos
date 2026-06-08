<!-- client/src/views/ProfilePanel.vue -->
<template>
  <div v-if="visible" class="modal-overlay" @click.self="$emit('close')">
    <div class="login-modal">
      <div class="modal-header">
        <h3>📊 个人档案</h3>
        <button class="modal-close" @click="$emit('close')">✕</button>
      </div>

      <div class="profile-body">
        <div class="profile-username">{{ roomStore.currentUser?.username }}</div>
        <div class="profile-stats">
          <div class="stat-card">
            <div class="stat-value">{{ roomStore.currentUser?.total_games || 0 }}</div>
            <div class="stat-label">总局数</div>
          </div>
          <div class="stat-card">
            <div class="stat-value">{{ roomStore.currentUser?.total_wins || 0 }}</div>
            <div class="stat-label">🥇 夺冠</div>
          </div>
          <div class="stat-card">
            <div class="stat-value">{{ roomStore.currentUser?.total_score || 0 }}</div>
            <div class="stat-label">总得分</div>
          </div>
        </div>
        <div v-if="roomStore.currentUser?.total_games" class="stat-extra">
          场均 {{ (roomStore.currentUser.total_score / roomStore.currentUser.total_games).toFixed(1) }} 分 ·
          胜率 {{ (roomStore.currentUser.total_wins / roomStore.currentUser.total_games * 100).toFixed(0) }}%
        </div>
        <p v-if="roomStore.currentUser?.created_at" class="stat-date">
          注册于 {{ roomStore.currentUser.created_at.slice(0, 10) }}
        </p>

        <button class="btn btn-secondary" @click="handleLogout">🚪 退出登录</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { useRoomStore } from '../stores/room'

defineProps({ visible: Boolean })
const emit = defineEmits(['close'])

const roomStore = useRoomStore()

async function handleLogout() {
  await roomStore.logout()
  emit('close')
}
</script>
