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

  // Mode 2 (WHO_IS_HONEST) state
  const myRole = ref(null)            // "honest" | "detective" | "bluffer"
  const roleDefinition = ref('')      // only for honest player: real definition prefill
  const detectiveGuessOptions = ref([])
  const detectiveGuessSubmitted = ref(false)
  const detectiveGuessResult = ref(null)
  const detectiveWrongAnswerIndices = ref([]) // wrong answer indices detective already tried
  const awaitingDetective = ref(false) // reveal phase: waiting for detective to guess
  const waitingForDetectiveVote = ref(false) // mode 2 voting phase: non-detective players wait

  // Round table: track who submitted / voted
  const submittedPlayers = ref([])
  const votedPlayers = ref([])

  // Ready-for-next state (both modes) — all players click ready to advance
  const readyPlayerIds = ref([])
  const readyCount = ref(0)
  const totalForReady = ref(0)
  const iAmReady = ref(false)

  const isJudge = computed(() => {
    const room = useRoomStore()
    return room.myPlayerId === judgeId.value
  })

  const isHonest = computed(() => myRole.value === 'honest')
  const isDetective = computed(() => myRole.value === 'detective')
  const isBluffer = computed(() => myRole.value === 'bluffer')

  const roleLabel = computed(() => {
    switch (myRole.value) {
      case 'honest': return '老实人'
      case 'detective': return '大聪明'
      case 'bluffer': return '瞎掰人'
      default: return ''
    }
  })

  function setPhase(phase, data) {
    if (phase === 'answering') {
      questionTerm.value = data.question_term || ''
      if (data.judge_id) judgeId.value = data.judge_id
      myAnswer.value = ''
      answerSubmitted.value = false
      voteCast.value = false
      submittedPlayers.value = []
      votedPlayers.value = []
      myVote.value = null
      voteOptions.value = []
      revealData.value = null
      awaitingDetective.value = false
    }
    if (phase === 'drawing') {
      if (data.judge_id) judgeId.value = data.judge_id
      answerSubmitted.value = false
      voteCast.value = false
      myVote.value = null
      voteOptions.value = []
      revealData.value = null
      awaitingDetective.value = false
      detectiveGuessSubmitted.value = false
      detectiveGuessResult.value = null
      detectiveWrongAnswerIndices.value = []
      waitingForDetectiveVote.value = false
    }
  }

  function updateFromMessage(msg) {
    switch (msg.type) {
      case 'phase_change':
        setPhase(msg.phase, msg)
        if (msg.waiting_for_detective_vote) {
          waitingForDetectiveVote.value = true
        }
        break
      case 'judge_info':
        questionTerm.value = msg.question_term
        judgeDefinition.value = msg.question_definition
        break
      case 'role_info':
        myRole.value = msg.role
        if (msg.question_definition) {
          roleDefinition.value = msg.question_definition
        }
        break
      case 'vote_options':
        voteOptions.value = msg.options
        break
      case 'reveal':
        revealData.value = msg
        if (msg.standings) standings.value = msg.standings
        if (msg.awaiting_detective) {
          awaitingDetective.value = true
        }
        break
      case 'detective_correct':
        // Mode 2: detective voted correctly → game over
        detectiveGuessResult.value = msg
        awaitingDetective.value = false
        waitingForDetectiveVote.value = false
        voteCast.value = true
        if (msg.standings) standings.value = msg.standings
        if (msg.answers) {
          revealData.value = { answers: msg.answers, correct_index: msg.correct_index }
        }
        if (msg.question_definition) {
          roleDefinition.value = msg.question_definition
        }
        if (msg.question_term) {
          questionTerm.value = msg.question_term
        }
        break
      case 'vote_wrong':
        // Mode 2: detective voted wrong — try again
        if (msg.wrong_index !== undefined) {
          detectiveWrongAnswerIndices.value.push(msg.wrong_index)
        }
        voteCast.value = false  // allow re-voting
        break
      case 'detective_retry':
        // Non-detective: detective is still trying
        waitingForDetectiveVote.value = true
        break
      case 'player_status':
        submittedPlayers.value = msg.submitted_players || []
        votedPlayers.value = msg.voted_players || []
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
      case 'ready_progress':
        readyPlayerIds.value = msg.ready_player_ids || []
        readyCount.value = msg.ready_count || 0
        totalForReady.value = msg.total_count || 0
        break
      case 'round_start':
        if (msg.standings) standings.value = msg.standings
        if (msg.next_judge_id) judgeId.value = msg.next_judge_id
        myRole.value = null
        roleDefinition.value = ''
        detectiveGuessOptions.value = []
        detectiveGuessSubmitted.value = false
        detectiveGuessResult.value = null
        detectiveWrongAnswerIndices.value = []
        awaitingDetective.value = false
        // Reset ready state
        submittedPlayers.value = []
        votedPlayers.value = []
        iAmReady.value = false
        readyPlayerIds.value = []
        readyCount.value = 0
        totalForReady.value = 0
        break
      case 'state_sync':
        // Full state restore on reconnect
        judgeId.value = msg.judge_id || ''
        if (msg.question_term) questionTerm.value = msg.question_term
        if (msg.question_definition) judgeDefinition.value = msg.question_definition
        if (msg.vote_options) voteOptions.value = msg.vote_options
        if (msg.standings) standings.value = msg.standings
        if (msg.answer_submitted) answerSubmitted.value = true
        if (msg.vote_cast) voteCast.value = true
        if (msg.my_role) {
          myRole.value = msg.my_role
          if (msg.question_definition && msg.my_role === 'honest') {
            roleDefinition.value = msg.question_definition
          }
        }
        if (msg.detective_wrong_indices) {
          detectiveWrongAnswerIndices.value = msg.detective_wrong_indices || []
        }
        if (msg.reveal_data) {
          revealData.value = msg.reveal_data
        }
        if (msg.ready_progress) {
          readyPlayerIds.value = msg.ready_progress.ready_player_ids || []
          readyCount.value = msg.ready_progress.ready_count || 0
          totalForReady.value = msg.ready_progress.total_count || 0
        }
        if (msg.waiting_for_detective_vote) {
          waitingForDetectiveVote.value = true
        }
        break
    }
  }

  return {
    questionTerm, judgeId, judgeDefinition, myAnswer, answerSubmitted,
    voteOptions, myVote, voteCast, revealData, standings, gameOver,
    isJudge, setPhase, updateFromMessage,
    // Mode 2
    myRole, roleDefinition, detectiveGuessOptions,
    detectiveGuessSubmitted, detectiveGuessResult, detectiveWrongAnswerIndices, awaitingDetective,
    isHonest, isDetective, isBluffer, roleLabel,
    waitingForDetectiveVote,
    // Round table
    submittedPlayers, votedPlayers,
    // Ready-for-next
    readyPlayerIds, readyCount, totalForReady, iAmReady,
  }
})
