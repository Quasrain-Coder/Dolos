<template>
  <div class="voting-panel">
    <!-- Mode 2: non-detective waiting screen -->
    <div v-if="gameStore.waitingForDetectiveVote" class="phase-waiting">
      <p>🕵️ 大聪明正在投票猜真定义...</p>
      <p class="waiting-sub">大聪明选对的那一刻，游戏就结束了!</p>
    </div>

    <!-- Normal voting -->
    <template v-else>
      <div class="question-card">
        <div class="label">选出「{{ gameStore.questionTerm }}」的真定义</div>
      </div>

      <div class="vote-options">
        <div
          v-for="opt in gameStore.voteOptions"
          :key="opt.index"
          class="vote-option"
          :class="{
            selected: selectedIndex === opt.index,
            eliminated: gameStore.detectiveWrongAnswerIndices.includes(opt.index)
          }"
          @click="selectOption(opt.index)"
        >
          <span class="letter">{{ letters[opt.index] }}</span>
          <div class="vote-option-content">
            <span class="text">{{ opt.text }}</span>
            <span v-if="opt.author" class="author-tag">{{ opt.author }}</span>
          </div>
          <span v-if="gameStore.detectiveWrongAnswerIndices.includes(opt.index)" class="eliminated-tag">❌</span>
        </div>
      </div>

      <button
        v-if="selectedIndex !== null && !gameStore.voteCast"
        class="btn btn-primary btn-lg"
        :disabled="gameStore.detectiveWrongAnswerIndices.includes(selectedIndex)"
        @click="castVote"
      >
        确认投票
      </button>
      <p v-if="gameStore.voteCast" class="voted-msg">✅ 已投票，等待揭晓...</p>
    </template>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useGameStore } from '../stores/game'
import { useWebSocket } from '../composables/useWebSocket'

const gameStore = useGameStore()
const { send } = useWebSocket()
const selectedIndex = ref(null)
const letters = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H']

function selectOption(index) {
  if (gameStore.voteCast) return
  if (gameStore.detectiveWrongAnswerIndices.includes(index)) return
  selectedIndex.value = index
}

function castVote() {
  if (selectedIndex.value === null) return
  if (gameStore.detectiveWrongAnswerIndices.includes(selectedIndex.value)) return
  gameStore.myVote = selectedIndex.value
  send('cast_vote', { answer_index: selectedIndex.value })
  // In mode 2, vote_wrong will reset voteCast; in mode 1, vote_cast confirms it
}
</script>
