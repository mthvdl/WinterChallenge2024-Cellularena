import { EndScreenModule } from './endscreen-module/EndScreenModule.js'
import { ViewModule, api } from './graphics/ViewModule.js'

export const modules = [
  ViewModule,
  EndScreenModule
]

export const playerColors = [
  '#ff5900', // orange
  '#2f9ecc', // blue
]
export const gameName = 'Sprawl'

export const stepByStepAnimateSpeed = 3

export const options = [
  {
    title: 'HIDE RANKING',
    get: function () {
      return api.options.debugMode
    },
    set: function (value) {
      api.setDebugMode(value)
    },
    values: {
      'ON': true,
      'OFF': false
    },
  }, {
    title: 'MY MESSAGES',
    get: function () {
      return api.options.showMyMessages
    },
    set: function (value) {
      api.options.showMyMessages = value
    },
    enabled: function () {
      return api.options.meInGame
    },
    values: {
      'ON': true,
      'OFF': false
    }
  }, {
    title: 'OTHERS\' MESSAGES',
    get: function () {
      return api.options.showOthersMessages
    },
    set: function (value) {
      api.options.showOthersMessages = value
    },

    values: {
      'ON': true,
      'OFF': false
    }
  }
]
