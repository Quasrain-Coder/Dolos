<!-- client/src/components/RevealPanel.vue -->
<template>
  <div class="reveal-panel" v-if="gameStore.revealData">
    <div class="section-title">🏆 揭晓结果</div>

    <!-- Mode 2: detective correct result -->
    <div v-if="gameStore.detectiveGuessResult" class="detective-result card">
      <div class="label">大聪明猜对了！</div>
      <div class="guess-outcome correct">
        ✅ {{ gameStore.detectiveGuessResult.wrong_count > 0 ? `试了 ${gameStore.detectiveGuessResult.wrong_count} 次后猜对` : '一次就猜对！' }}
      </div>
      <div class="guess-detail">
        老实人是 <strong>{{ gameStore.detectiveGuessResult.honest_nickname }}</strong>
      </div>
    </div>

    <!-- Correct definition (mode 2) -->
    <div v-if="gameStore.roleDefinition" class="correct-answer card">
      <div class="label">📖 正确释义</div>
      <div class="text">{{ gameStore.roleDefinition }}</div>
    </div>

    <!-- Correct answer -->
    <div v-if="correctAnswer" class="correct-answer card">
      <div class="label">正确答案</div>
      <div class="text">{{ correctAnswer?.text }}</div>
      <div class="meta" v-if="correctAnswer?.author && correctAnswer.author !== '?'">{{ correctAnswer?.author }}</div>
    </div>

    <!-- All answers with vote counts -->
    <div class="card" v-if="revealAnswers.length > 0">
      <div v-for="a in revealAnswers" :key="a.index" class="answer-row" :class="{ correct: a.is_real, voted: myVoteIndex === a.index }">
        <span class="letter">{{ letters[a.index] }}</span>
        <div class="answer-content">
          <div class="answer-text">{{ a.text }}</div>
          <div class="answer-meta">
            <template v-if="a.author && a.author !== '?'">{{ a.author }}</template>
            <span v-if="myVoteIndex === a.index">← 你投了</span>
          </div>
        </div>
        <span class="vote-badge">{{ a.vote_count }}票</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useGameStore } from '../stores/game'
import { useRoomStore } from '../stores/room'

const gameStore = useGameStore()
const roomStore = useRoomStore()
const letters = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H']

const correctAnswer = computed(() => {
  if (!gameStore.revealData?.answers) return null
  return gameStore.revealData.answers.find(a => a.is_real) || null
})

const myVoteIndex = computed(() => gameStore.myVote)

const revealAnswers = computed(() => {
  return gameStore.revealData?.answers || []
})
</script>
