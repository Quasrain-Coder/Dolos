<template>
  <div v-if="visible" class="question-picker">
    <div class="picker-header">
      <h3>🕵️ 大聪明 — 选择一道题</h3>
      <p class="picker-hint">从以下三题中选择一道作为本回合题目</p>
    </div>

    <div class="candidate-list">
      <div
        v-for="(q, i) in candidates"
        :key="i"
        class="candidate-card"
        :class="{ selected: selectedIndex === i }"
        @click="selectedIndex = i"
      >
        <span class="candidate-tag">{{ q.category }}</span>
        <span class="candidate-term">{{ q.term }}</span>
      </div>
    </div>

    <div class="picker-actions">
      <button class="btn btn-secondary" @click="$emit('refresh')" :disabled="refreshing">
        {{ refreshing ? '🔄 刷新中...' : '🔄 换一批' }}
      </button>
      <button
        class="btn btn-primary"
        :disabled="selectedIndex === null || confirming"
        @click="confirmPick"
      >
        {{ confirming ? '⏳' : '✅ 就选这个' }}
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'

const props = defineProps({
  visible: Boolean,
  candidates: { type: Array, default: () => [] },
})
const emit = defineEmits(['refresh', 'select'])

const selectedIndex = ref(null)
const confirming = ref(false)
const refreshing = ref(false)

watch(() => props.candidates, () => {
  selectedIndex.value = null
  confirming.value = false
  refreshing.value = false
})

function confirmPick() {
  if (selectedIndex.value === null) return
  confirming.value = true
  emit('select', selectedIndex.value)
}
</script>
