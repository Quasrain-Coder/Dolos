// client/src/stores/game.js
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { useRoomStore } from './room'

export const useGameStore = defineStore('game', () => {
  const questionTerm = ref('')
  const judgeId = ref('')
  const judgeDefinition = ref('')
  const myAnswer = ref('')
  const answerSubmitted = ref(false)
  const voteOptions = ref([])
  const myVote = ref(null)
  const voteCast = ref(false)
  const revealData = ref(null)
  const standings = ref([])
  const gameOver = ref(false)

  const isJudge = computed(() => {
    const room = useRoomStore()
    return room.myPlayerId === judgeId.value
  })

  function setPhase(phase, data) {
    if (phase === 'answering') {
      questionTerm.value = data.question_term || ''
      judgeId.value = data.judge_id || ''
      myAnswer.value = ''
      answerSubmitted.value = false
      voteCast.value = false
      myVote.value = null
      voteOptions.value = []
      revealData.value = null
    }
    if (phase === 'drawing') {
      answerSubmitted.value = false
      voteCast.value = false
      myVote.value = null
      voteOptions.value = []
      revealData.value = null
    }
  }

  function updateFromMessage(msg) {
    switch (msg.type) {
      case 'phase_change':
        setPhase(msg.phase, msg)
        break
      case 'judge_info':
        questionTerm.value = msg.question_term
        judgeDefinition.value = msg.question_definition
        break
      case 'vote_options':
        voteOptions.value = msg.options
        break
      case 'reveal':
        revealData.value = msg
        if (msg.standings) standings.value = msg.standings
        break
      case 'answer_submitted':
        answerSubmitted.value = true
        break
      case 'vote_cast':
        voteCast.value = true
        break
      case 'game_over':
        gameOver.value = true
        if (msg.standings) standings.value = msg.standings
        break
      case 'round_start':
        if (msg.standings) standings.value = msg.standings
        judgeId.value = msg.next_judge_id
        break
    }
  }

  return {
    questionTerm, judgeId, judgeDefinition, myAnswer, answerSubmitted,
    voteOptions, myVote, voteCast, revealData, standings, gameOver,
    isJudge, setPhase, updateFromMessage,
  }
})
