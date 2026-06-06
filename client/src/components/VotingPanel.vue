<template>
  <div class="voting-panel">
    <div class="question-card">
      <div class="label">选出「{{ gameStore.questionTerm }}」的真定义</div>
    </div>

    <div class="vote-options">
      <div
        v-for="opt in gameStore.voteOptions"
        :key="opt.index"
        class="vote-option"
        :class="{ selected: selectedIndex === opt.index }"
        @click="selectOption(opt.index)"
      >
        <span class="letter">{{ letters[opt.index] }}</span>
        <span class="text">{{ opt.text }}</span>
      </div>
    </div>

    <button v-if="selectedIndex !== null && !gameStore.voteCast" class="btn btn-primary btn-lg" @click="castVote">确认投票</button>
    <p v-if="gameStore.voteCast" class="voted-msg">✅ 已投票，等待揭晓...</p>
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
  selectedIndex.value = index
}

function castVote() {
  if (selectedIndex.value === null) return
  gameStore.myVote = selectedIndex.value
  send('cast_vote', { answer_index: selectedIndex.value })
}
</script>
