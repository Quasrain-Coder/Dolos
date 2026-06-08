<!-- client/src/components/PlayerStatsPopup.vue -->
<template>
  <div v-if="stats" class="stats-popup" @click.stop>
    <div class="stats-username">{{ stats.username }}</div>
    <div class="stats-row">
      <span>总局数 <strong>{{ stats.total_games }}</strong></span>
      <span>🥇 <strong>{{ stats.total_wins }}</strong></span>
      <span>总分 <strong>{{ stats.total_score }}</strong></span>
    </div>
    <div v-if="stats.total_games" class="stats-extra-popup">
      场均 {{ (stats.total_score / stats.total_games).toFixed(1) }} ·
      胜率 {{ (stats.total_wins / stats.total_games * 100).toFixed(0) }}%
    </div>
    <button class="stats-close" @click="$emit('close')">✕</button>
  </div>
  <div v-if="loading" class="stats-popup stats-loading">加载中...</div>
</template>

<script setup>
import { ref, watch } from 'vue'

const props = defineProps({
  userId: { type: Number, default: null },
})
defineEmits(['close'])

const stats = ref(null)
const loading = ref(false)

watch(() => props.userId, async (uid) => {
  stats.value = null
  if (!uid) return
  loading.value = true
  try {
    const resp = await fetch(`/api/users/${uid}`)
    if (resp.ok) {
      stats.value = await resp.json()
    }
  } catch {}
  loading.value = false
}, { immediate: true })
</script>
