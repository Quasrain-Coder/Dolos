<!-- client/src/components/DetectiveGuessPanel.vue -->
<template>
  <div class="detective-guess-panel">
    <div class="card detective-card">
      <div class="detective-badge">🕵️ 你是大聪明！</div>
      <p class="detective-prompt">请猜猜谁是老实人（提交了真定义的人）</p>

      <!-- Wrong guesses so far -->
      <div v-if="gameStore.detectiveWrongGuesses.length > 0" class="wrong-guesses">
        <div class="wrong-label">❌ 已排除：</div>
        <div class="wrong-list">
          <span v-for="w in gameStore.detectiveWrongGuesses" :key="w.player_id" class="wrong-tag">
            ❌ {{ w.nickname || getPlayerName(w.player_id) }}
          </span>
        </div>
      </div>

      <!-- Remaining options -->
      <div class="guess-options">
        <div
          v-for="p in availableOptions"
          :key="p.id"
          class="guess-option"
          :class="{ selected: selectedId === p.id }"
          @click="selectedId = p.id"
        >
          <span class="guess-icon">{{ selectedId === p.id ? '✅' : '🎭' }}</span>
          <span class="guess-name">{{ p.nickname }}</span>
        </div>
      </div>

      <div v-if="availableOptions.length === 0" class="no-options">
        <p>所有玩家都已猜过？再确认一下...</p>
      </div>

      <button
        v-if="availableOptions.length > 0"
        class="btn btn-primary btn-lg"
        :disabled="!selectedId"
        @click="submitGuess"
      >
        确认猜测
      </button>

      <!-- Result display when correct -->
      <div v-if="gameStore.detectiveGuessResult" class="guess-success">
        <div class="success-badge">🎉 猜对了！</div>
        <p>老实人是 <strong>{{ gameStore.detectiveGuessResult.honest_nickname }}</strong></p>
        <div v-if="gameStore.roleDefinition" class="definition-reveal">
          <div class="label">📖 正确释义</div>
          <div class="ref-text">{{ gameStore.roleDefinition }}</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useGameStore } from '../stores/game'
import { useRoomStore } from '../stores/room'
import { useWebSocket } from '../composables/useWebSocket'

const gameStore = useGameStore()
const roomStore = useRoomStore()
const { send } = useWebSocket()
const selectedId = ref(null)

// Filter out wrong-guessed players from options
const availableOptions = computed(() => {
  const wrongIds = new Set(gameStore.detectiveWrongGuesses.map(w => w.player_id))
  return gameStore.detectiveGuessOptions.filter(p => !wrongIds.has(p.id))
})

function getPlayerName(pid) {
  const p = roomStore.players.find(p => p.id === pid)
  return p ? p.nickname : '?'
}

function submitGuess() {
  if (!selectedId.value) return
  send('detective_guess', { guessed_player_id: selectedId.value })
  selectedId.value = null
}
</script>
