<template>
  <div class="reveal-panel" v-if="gameStore.revealData">
    <div class="section-title">🏆 揭晓结果</div>

    <div class="correct-answer card">
      <div class="label">正确答案</div>
      <div class="text">{{ correctAnswer?.text }}</div>
      <div class="meta">{{ correctAnswer?.author }}</div>
    </div>

    <div class="card">
      <div v-for="a in gameStore.revealData.answers" :key="a.index" class="answer-row" :class="{ correct: a.is_real, voted: myVoteIndex === a.index }">
        <span class="letter">{{ letters[a.index] }}</span>
        <div class="answer-content">
          <div class="answer-text">{{ a.text }}</div>
          <div class="answer-meta">{{ a.author }}<span v-if="myVoteIndex === a.index">← 你投了</span></div>
        </div>
        <span class="vote-badge">{{ a.vote_count }}票</span>
      </div>
    </div>

    <div class="card" v-if="gameStore.revealData.scores && Object.keys(gameStore.revealData.scores).length">
      <div class="label">本回合得分</div>
      <div v-for="(s, pid) in gameStore.revealData.scores" :key="pid" class="score-row">✅ {{ s.nickname }} +{{ s.pts }}分</div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useGameStore } from '../stores/game'

const gameStore = useGameStore()
const letters = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H']

const correctAnswer = computed(() => {
  if (!gameStore.revealData) return null
  return gameStore.revealData.answers.find(a => a.is_real) || null
})

const myVoteIndex = computed(() => gameStore.myVote)
</script>
