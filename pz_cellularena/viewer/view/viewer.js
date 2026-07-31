var CellularenaViewer = (() => {
  var __defProp = Object.defineProperty;
  var __getOwnPropDesc = Object.getOwnPropertyDescriptor;
  var __getOwnPropNames = Object.getOwnPropertyNames;
  var __hasOwnProp = Object.prototype.hasOwnProperty;
  var __export = (target, all) => {
    for (var name in all)
      __defProp(target, name, { get: all[name], enumerable: true });
  };
  var __copyProps = (to, from, except, desc) => {
    if (from && typeof from === "object" || typeof from === "function") {
      for (let key of __getOwnPropNames(from))
        if (!__hasOwnProp.call(to, key) && key !== except)
          __defProp(to, key, { get: () => from[key], enumerable: !(desc = __getOwnPropDesc(from, key)) || desc.enumerable });
    }
    return to;
  };
  var __toCommonJS = (mod) => __copyProps(__defProp({}, "__esModule", { value: true }), mod);

  // ts/main.ts
  var main_exports = {};
  __export(main_exports, {
    ViewModule: () => ViewModule,
    setRenderer: () => setRenderer
  });

  // ts/core/constants.ts
  var WIDTH = 1920;
  var HEIGHT = 1080;

  // ts/core/transitions.ts
  function bell(t) {
    return Math.sin(t * Math.PI);
  }
  function easeOut(t) {
    return t * (2 - t);
  }

  // ts/core/utils.ts
  function lerp(a, b, u) {
    return a + (b - a) * u;
  }
  function unlerp(a, b, v) {
    if (a === b) return 0;
    return Math.max(0, Math.min(1, (v - a) / (b - a)));
  }
  function lerpPosition(from, to, p) {
    return { x: lerp(from.x, to.x, p), y: lerp(from.y, to.y, p) };
  }
  function fitAspectRatio(srcWidth, srcHeight, maxWidth, maxHeight, padding = 0) {
    return Math.min((maxWidth - padding * 2) / srcWidth, (maxHeight - padding * 2) / srcHeight);
  }

  // ts/graphics/Deserializer.ts
  function parseData(unsplit, globalData) {
    const raw = unsplit.split("\n");
    let idx = 0;
    const storage = [];
    const messages = [];
    for (let playerIdx = 0; playerIdx < globalData.playerCount; ++playerIdx) {
      const playerStorage = [];
      const playerMessages = {};
      raw[idx++].split(" ").forEach((x) => playerStorage.push(+x));
      storage.push(playerStorage);
      const messageCount = +raw[idx++];
      for (let i = 0; i < messageCount; ++i) {
        const message = raw[idx++].split(" ");
        const organId = +message[0];
        const text = message.slice(1).join(" ");
        playerMessages[organId] = text;
      }
      messages.push(playerMessages);
    }
    const events = [];
    const eventCount = +raw[idx++];
    for (let i = 0; i < eventCount; ++i) {
      const type = +raw[idx++];
      const start = +raw[idx++];
      const end = +raw[idx++];
      const playerIdx = +raw[idx++];
      const id = +raw[idx++];
      const organType = raw[idx++];
      const direction = raw[idx++];
      const coords = raw[idx++].split("_").map((xy) => parseCoord(xy));
      const animData = { start, end };
      events.push({
        playerIdx,
        id,
        type,
        animData,
        coord: coords[0],
        target: coords[1],
        coords,
        organType,
        direction
      });
    }
    return {
      events,
      storage,
      messages
    };
  }
  function parseGlobalData(unsplit) {
    const raw = unsplit.split("\n");
    let idx = 0;
    let line = raw[idx++].split(" ");
    const width = +line[0];
    const height = +line[1];
    const tiles = [];
    for (let y = 0; y < height; y++) {
      for (let x = 0; x < width; x++) {
        const line2 = raw[idx++].split(" ");
        const obstacle = line2[0] === "1";
        const protein = line2[1];
        tiles.push({ obstacle, protein });
      }
    }
    const organs = [];
    for (let playerIdx = 0; playerIdx < 2; ++playerIdx) {
      const playerOrgans = [];
      const organCount = +raw[idx++];
      for (let i = 0; i < organCount; i++) {
        const rawOrgan = raw[idx++].split(" ");
        let oIdx = 0;
        const organ = {
          id: +rawOrgan[oIdx++],
          pos: { x: +rawOrgan[oIdx++], y: +rawOrgan[oIdx++] },
          type: rawOrgan[oIdx++],
          direction: rawOrgan[oIdx++],
          parentId: +rawOrgan[oIdx++],
          playerIdx
        };
        playerOrgans.push(organ);
      }
      organs.push(playerOrgans);
    }
    return {
      width,
      height,
      organs,
      tiles
    };
  }
  function parseCoord(coord) {
    const [x, y] = coord.split(" ").map((x2) => +x2);
    return { x, y };
  }

  // ts/graphics/TooltipManager.ts
  var PADDING = 5;
  var CURSOR_WIDTH = 20;
  function generateText(text, size, color, align) {
    var textEl = new PIXI.Text(text, {
      fontSize: Math.round(size / 1.2) + "px",
      fontFamily: "Monospace",
      fontWeight: "bold",
      fill: color,
      lineHeight: size
    });
    if (align === "right") {
      textEl.anchor.x = 1;
    } else if (align === "center") {
      textEl.anchor.x = 0.5;
    }
    return textEl;
  }
  var TooltipManager = class {
    reinit() {
      const container = new PIXI.Container();
      const tooltip = new PIXI.Container();
      const background = new PIXI.Graphics();
      const label = generateText("DEFAULT", 36, 16777215, "left");
      label.position.x = PADDING;
      label.position.y = PADDING;
      tooltip.visible = false;
      tooltip.addChild(background);
      tooltip.addChild(label);
      this.tooltipBackground = background;
      this.tooltipLabel = label;
      this.tooltipContainer = container;
      this.tooltip = tooltip;
      this.registry = [];
      this.inside = {};
      this.tooltipOffset = 0;
      this.getGlobalText = null;
      container.addChild(this.tooltip);
      return container;
    }
    clear() {
      this.inside = {};
    }
    registerGlobal(getText) {
      this.getGlobalText = getText;
    }
    register(element, getText) {
      const registryIdx = this.registry.length;
      this.registry.push({ element, getText });
      element.on("mouseover", () => {
        this.inside[registryIdx] = true;
      });
      element.on("mouseout", () => {
        delete this.inside[registryIdx];
      });
    }
    showTooltip(text) {
      this.setTooltipText(this.tooltip, text);
    }
    setTooltipText(tooltip, text) {
      this.tooltipLabel.text = text;
      const width = this.tooltipLabel.width + PADDING * 2;
      const height = this.tooltipLabel.height + PADDING * 2;
      this.tooltipOffset = -width;
      this.tooltipBackground.clear();
      this.tooltipBackground.beginFill(0, 0.9);
      this.tooltipBackground.drawRect(0, 0, width, height);
      this.tooltipBackground.endFill();
      tooltip.visible = true;
    }
    updateGlobalText() {
      if (this.lastEvent != null) {
        this.moveTooltip(this.lastEvent);
      }
    }
    moveTooltip(event) {
      this.lastEvent = event;
      const newPosition = event.data.getLocalPosition(this.tooltipContainer);
      let xOffset = this.tooltipOffset - 10;
      let yOffset = -20;
      if (newPosition.x + xOffset < 0) {
        xOffset = CURSOR_WIDTH;
      }
      if (newPosition.y + this.tooltip.height > HEIGHT) {
        yOffset = HEIGHT - newPosition.y - this.tooltip.height;
      }
      this.tooltip.position.x = newPosition.x + xOffset;
      this.tooltip.position.y = newPosition.y + yOffset;
      const textBlocks = [];
      for (const key of Object.keys(this.inside)) {
        const registryIdx = parseInt(key);
        const { getText } = this.registry[registryIdx];
        const text = getText(newPosition.x);
        if (text != null && text.length > 0) {
          textBlocks.push(text);
        }
      }
      if (this.getGlobalText != null) {
        const text = this.getGlobalText(event.data);
        if (text != null && text.length > 0) {
          textBlocks.push(text);
        }
      }
      if (textBlocks.length > 0) {
        this.showTooltip(textBlocks.join("\n--------\n"));
      } else {
        this.hideTooltip();
      }
    }
    hideTooltip() {
      this.tooltip.visible = false;
    }
  };

  // ts/graphics/utils.ts
  function setAnimationProgress(fx, progress) {
    let idx = Math.floor(progress * fx.totalFrames);
    idx = Math.min(fx.totalFrames - 1, idx);
    fx.gotoAndStop(idx);
    return idx;
  }
  function fit(entity, maxWidth, maxHeight) {
    entity.scale.set(fitAspectRatio(entity.width, entity.height, maxWidth, maxHeight));
  }
  function last(arr) {
    return arr[arr.length - 1];
  }

  // ts/graphics/assetConstants.ts
  var ABORPTION_FRAMES = [
    "Absorption0052",
    "Absorption0054",
    "Absorption0056",
    "Absorption0058",
    "Absorption0060",
    "Absorption0062",
    "Absorption0064",
    "Absorption0066",
    "Absorption0068",
    "Absorption0070",
    "Absorption0072",
    "Absorption0074",
    "Absorption0076",
    "Absorption0078",
    "Absorption0080",
    "Absorption0082",
    "Absorption0084",
    "Absorption0086",
    "Absorption0088",
    "Absorption0090",
    "Absorption0092",
    "Absorption0094",
    "Absorption0096"
  ];
  var WALL_SPAWN_FRAMES = [
    "MurCreation0001",
    "MurCreation0003",
    "MurCreation0005",
    "MurCreation0007",
    "MurCreation0009",
    "MurCreation0011",
    "MurCreation0013",
    "MurCreation0015",
    "MurCreation0017",
    "MurCreation0019",
    "MurCreation0021",
    "MurCreation0023",
    "MurCreation0025",
    "MurCreation0027"
  ];
  var BLUE_DEATH_FRAMES = [
    "BleuDeath0019",
    "OrangeDeath0021",
    "BleuDeath0023",
    "BleuDeath0025",
    "BleuDeath0027",
    "BleuDeath0029",
    "BleuDeath0033",
    "BleuDeath0033",
    "BleuDeath0035",
    "BleuDeath0037",
    "BleuDeath0039",
    "BleuDeath0041",
    "BleuDeath0043",
    "BleuDeath0047",
    "BleuDeath0047",
    "BleuDeath0049",
    "BleuDeath0051",
    "BleuDeath0053",
    "BleuDeath0055",
    "BleuDeath0057",
    "BleuDeath0059",
    "BleuDeath0061",
    "BleuDeath0063",
    "BleuDeath0063",
    "BleuDeath0067"
  ];
  var BLUE_GROW_FRAMES = [
    "BleuGrow0001",
    "BleuGrow0001",
    "BleuGrow0001",
    "BleuGrow0009",
    "BleuGrow0009",
    "BleuGrow0009",
    "BleuGrow0015",
    "BleuGrow0015",
    "BleuGrow0015",
    "BleuGrow0023",
    "BleuGrow0023",
    "BleuGrow0023",
    "BleuGrow0027",
    "BleuGrow0027",
    "BleuGrow0027",
    "BleuGrow0035",
    "BleuGrow0035",
    "BleuGrow0035",
    "BleuGrow0041",
    "BleuGrow0041",
    "BleuGrow0041",
    "BleuGrow0047",
    "BleuGrow0047",
    "BleuGrow0047"
  ];
  var BLUE_HARVEST_FRAMES = [
    "BleuRecolteurMiam0003",
    "BleuRecolteurMiam0003",
    "BleuRecolteurMiam0005",
    "BleuRecolteurMiam0007",
    "BleuRecolteurMiam0009",
    "BleuRecolteurMiam0011",
    "BleuRecolteurMiam0013",
    "BleuRecolteurMiam0015",
    "BleuRecolteurMiam0017",
    "BleuRecolteurMiam0019",
    "BleuRecolteurMiam0021",
    "BleuRecolteurMiam0023",
    "BleuRecolteurMiam0025",
    "BleuRecolteurMiam0027",
    "BleuRecolteurMiam0029",
    "BleuRecolteurMiam0031",
    "BleuRecolteurMiam0033",
    "BleuRecolteurMiam0035"
  ];
  var BLUE_SPORE_FRAMES = [
    "BleuSporeurGraine0001",
    "BleuSporeurGraine0003",
    "BleuSporeurGraine0005",
    "BleuSporeurGraine0007",
    "BleuSporeurGraine0009",
    "BleuSporeurGraine0011",
    "BleuSporeurGraine0013",
    "BleuSporeurGraine0015",
    "BleuSporeurGraine0017",
    "BleuSporeurGraine0019",
    "BleuSporeurGraine0021",
    "BleuSporeurGraine0023",
    "BleuSporeurGraine0025",
    "BleuSporeurGraine0027",
    "BleuSporeurGraine0029",
    "BleuSporeurGraine0031",
    "BleuSporeurGraine0033",
    "BleuSporeurGraine0035",
    "BleuSporeurGraine0037",
    "BleuSporeurGraine0039",
    "BleuSporeurGraine0041",
    "BleuSporeurGraine0043",
    "BleuSporeurGraine0045",
    "BleuSporeurGraine0047",
    "BleuSporeurGraine0049"
  ];
  var BLUE_ATTACK_FRAMES = [
    "BleuTentAttaque0001",
    "BleuTentAttaque0003",
    "BleuTentAttaque0005",
    "BleuTentAttaque0007",
    "BleuTentAttaque0009",
    "BleuTentAttaque0011",
    "BleuTentAttaque0013",
    "BleuTentAttaque0015",
    "BleuTentAttaque0017",
    "BleuTentAttaque0019",
    "BleuTentAttaque0021",
    "BleuTentAttaque0023",
    "BleuTentAttaque0025",
    "BleuTentAttaque0027",
    "BleuTentAttaque0029",
    "BleuTentAttaque0031",
    "BleuTentAttaque0033",
    "BleuTentAttaque0035",
    "BleuTentAttaque0037",
    "BleuTentAttaque0039",
    "BleuTentAttaque0041",
    "BleuTentAttaque0043",
    "BleuTentAttaque0045",
    "BleuTentAttaque0047",
    "BleuTentAttaque0049"
  ];
  var ORANGE_DEATH_FRAMES = [
    "BleuDeath0019",
    "OrangeDeath0021",
    "OrangeDeath0023",
    "OrangeDeath0025",
    "OrangeDeath0027",
    "OrangeDeath0029",
    "OrangeDeath0033",
    "OrangeDeath0033",
    "OrangeDeath0035",
    "OrangeDeath0037",
    "OrangeDeath0039",
    "OrangeDeath0041",
    "OrangeDeath0043",
    "OrangeDeath0047",
    "OrangeDeath0047",
    "OrangeDeath0049",
    "OrangeDeath0051",
    "OrangeDeath0053",
    "OrangeDeath0055",
    "OrangeDeath0057",
    "OrangeDeath0059",
    "OrangeDeath0061",
    "OrangeDeath0063",
    "OrangeDeath0063",
    "OrangeDeath0067"
  ];
  var ORANGE_GROW_FRAMES = [
    "OrangeGrow0001",
    "OrangeGrow0001",
    "OrangeGrow0001",
    "OrangeGrow0007",
    "OrangeGrow0007",
    "OrangeGrow0007",
    "OrangeGrow0013",
    "OrangeGrow0013",
    "OrangeGrow0013",
    "OrangeGrow0023",
    "OrangeGrow0023",
    "OrangeGrow0023",
    "OrangeGrow0025",
    "OrangeGrow0025",
    "OrangeGrow0025",
    "OrangeGrow0033",
    "OrangeGrow0033",
    "OrangeGrow0033",
    "OrangeGrow0037",
    "OrangeGrow0037",
    "OrangeGrow0037",
    "OrangeGrow0045",
    "OrangeGrow0045",
    "OrangeGrow0045"
  ];
  var ORANGE_HARVEST_FRAMES = [
    "OrangeRecolteurMiam0003",
    "OrangeRecolteurMiam0003",
    "OrangeRecolteurMiam0005",
    "OrangeRecolteurMiam0007",
    "OrangeRecolteurMiam0009",
    "OrangeRecolteurMiam0011",
    "OrangeRecolteurMiam0013",
    "OrangeRecolteurMiam0015",
    "OrangeRecolteurMiam0017",
    "OrangeRecolteurMiam0019",
    "OrangeRecolteurMiam0021",
    "OrangeRecolteurMiam0023",
    "OrangeRecolteurMiam0025",
    "OrangeRecolteurMiam0027",
    "OrangeRecolteurMiam0029",
    "OrangeRecolteurMiam0031",
    "OrangeRecolteurMiam0033",
    "OrangeRecolteurMiam0035"
  ];
  var ORANGE_SPORE_FRAMES = [
    "OrangeSporeurGraine0001",
    "OrangeSporeurGraine0003",
    "OrangeSporeurGraine0005",
    "OrangeSporeurGraine0007",
    "OrangeSporeurGraine0009",
    "OrangeSporeurGraine0011",
    "OrangeSporeurGraine0013",
    "OrangeSporeurGraine0015",
    "OrangeSporeurGraine0017",
    "OrangeSporeurGraine0019",
    "OrangeSporeurGraine0021",
    "OrangeSporeurGraine0023",
    "OrangeSporeurGraine0025",
    "OrangeSporeurGraine0027",
    "OrangeSporeurGraine0029",
    "OrangeSporeurGraine0031",
    "OrangeSporeurGraine0033",
    "OrangeSporeurGraine0035",
    "OrangeSporeurGraine0037",
    "OrangeSporeurGraine0039",
    "OrangeSporeurGraine0041",
    "OrangeSporeurGraine0043",
    "OrangeSporeurGraine0045",
    "OrangeSporeurGraine0047",
    "OrangeSporeurGraine0049"
  ];
  var ORANGE_ATTACK_FRAMES = [
    "OrangeTentAttaque0001",
    "OrangeTentAttaque0003",
    "OrangeTentAttaque0005",
    "OrangeTentAttaque0007",
    "OrangeTentAttaque0009",
    "OrangeTentAttaque0011",
    "OrangeTentAttaque0013",
    "OrangeTentAttaque0015",
    "OrangeTentAttaque0017",
    "OrangeTentAttaque0019",
    "OrangeTentAttaque0021",
    "OrangeTentAttaque0023",
    "OrangeTentAttaque0025",
    "OrangeTentAttaque0027",
    "OrangeTentAttaque0029",
    "OrangeTentAttaque0031",
    "OrangeTentAttaque0033",
    "OrangeTentAttaque0035",
    "OrangeTentAttaque0037",
    "OrangeTentAttaque0039",
    "OrangeTentAttaque0041",
    "OrangeTentAttaque0043",
    "OrangeTentAttaque0045",
    "OrangeTentAttaque0047",
    "OrangeTentAttaque0049"
  ];
  var SPORE_PARTICLES = [
    "BlobOrangeGraine",
    "BlobBleuGraine"
  ];
  var DEATH_FRAMES = [
    ORANGE_DEATH_FRAMES,
    BLUE_DEATH_FRAMES
  ];
  var SPORE_FRAMES = [
    ORANGE_SPORE_FRAMES,
    BLUE_SPORE_FRAMES
  ];
  var ATTACK_FRAMES = [
    ORANGE_ATTACK_FRAMES,
    BLUE_ATTACK_FRAMES
  ];
  var GROW_FRAMES = [
    ORANGE_GROW_FRAMES,
    BLUE_GROW_FRAMES
  ];
  var HARVEST_FRAMES = [
    ORANGE_HARVEST_FRAMES,
    BLUE_HARVEST_FRAMES
  ];
  var ORGANS = [
    {
      BASIC: "BlobOrangeBasique",
      HARVESTER: HARVEST_FRAMES[0][0],
      ROOT: "BlobOrangeNoyeau",
      SPORER: SPORE_FRAMES[0][0],
      TENTACLE: ATTACK_FRAMES[0][0]
    },
    {
      BASIC: "BlobBleuBasique",
      HARVESTER: HARVEST_FRAMES[1][0],
      ROOT: "BlobBleuNoyeau",
      SPORER: SPORE_FRAMES[1][0],
      TENTACLE: ATTACK_FRAMES[1][0]
    }
  ];
  var ROOT_STATES = [
    {
      ATTACK: "BlobOrangeForce",
      HARVEST: "BlobOrangeJoyeux",
      DEATH: "BlobOrangeTriste"
    },
    {
      ATTACK: "BlobBleuForce",
      HARVEST: "BlobBleuJoyeux",
      DEATH: "BlobBleuTriste"
    }
  ];
  var ABSORPTION_ANCHOR = {
    x: 127 / 267,
    y: 129 / 263
  };
  var DEATH_ANCHOR = {
    x: (78 + 192 / 2) / 354,
    y: (97 + 192 / 2) / 326
  };
  var WALL_SPAWN_ANCHOR = {
    x: (111 + 177 / 2 + 1) / 388,
    y: (104 + 177 / 2 + 1) / 372
  };
  var ORGAN_ANCHORS = {
    BASIC: { x: 0.5, y: 0.5 },
    HARVESTER: { x: 84 / 503, y: 0.5 },
    ROOT: { x: 0.5, y: 0.5 },
    SPORER: {
      x: (239 + 72) / 2 / 412,
      y: (186 + 19) / 2 / 205
    },
    TENTACLE: {
      x: (73 + 241) / 2 / 581,
      y: (262 + 95) / 2 / 329
    }
  };
  var AVATAR_RECT = {
    x: 13,
    y: 11,
    w: 100,
    h: 100
  };
  var NAME_RECT = {
    x: 149,
    y: 12,
    w: 373,
    h: 44
  };
  var SCORE_RECT = {
    x: 558,
    y: 12,
    w: 152,
    h: 44
  };
  var PROTEIN_RECT = {
    x: 208,
    y: 76,
    w: 59,
    h: 33
  };
  var PROTEIN_SEP = 139;
  var GAME_ZONE_RECT = {
    x: 53,
    y: 159,
    w: 1820,
    h: 909
  };
  var ORGAN_TILE_PADDING = 5;
  var ORGANS_ANIMATIONS_VALUES = {
    growth: {
      frames: GROW_FRAMES.map((v) => v.filter((_, idx) => idx % 3 === 0))
    },
    death: {
      frames: DEATH_FRAMES.map((v) => v.filter((_, idx) => idx % 2 === 0)),
      anchors: DEATH_ANCHOR
    },
    harvest: {
      frames: HARVEST_FRAMES.map((v) => v.filter((_, idx) => idx % 2 === 0)),
      anchors: ORGAN_ANCHORS["HARVESTER"]
    },
    spore: {
      frames: SPORE_FRAMES.map((v) => v.filter((_, idx) => idx % 3 === 0)),
      anchors: ORGAN_ANCHORS["SPORER"]
    },
    attack: {
      frames: ATTACK_FRAMES.map((v) => v.filter((_, idx) => idx % 3 === 0)),
      anchors: ORGAN_ANCHORS["TENTACLE"]
    }
  };
  var ROTATIONS_MAP = { N: -Math.PI / 2, E: 0, W: Math.PI, S: Math.PI / 2 };

  // ts/graphics/gameConstants.ts
  var GRID_LINE_WIDTH = 2;
  var HUD_COLORS = [16603393, 3386828];

  // ts/graphics/events.ts
  var events_default = {
    GROW: 0,
    SPORE: 1,
    ATTACK: 2,
    DEATH: 3,
    HARVEST: 5,
    ABSORB: 6,
    CRASH: 7,
    SPAWN_ROOT: 8
  };

  // ts/core/rendering.ts
  var _renderer = null;
  var _destroyList = [];
  function setRenderer(r) {
    _renderer = r;
  }
  function getRenderer() {
    return _renderer;
  }
  function flagForDestructionOnReinit(obj) {
    _destroyList.push(obj);
  }

  // ts/graphics/MessageBoxes.ts
  function renderMessageContainer(messageContainer, i, step) {
    const playerInfo = this.globalData.players;
    const options = this.api.options;
    const stepFactor = Math.pow(0.99, step);
    const targetMessageAlpha = options.showMyMessages && playerInfo[i].isMe || options.showOthersMessages && !playerInfo[i].isMe ? 1 : 0;
    messageContainer.alpha = messageContainer.alpha * stepFactor + targetMessageAlpha * (1 - stepFactor);
  }
  var messageBox = {
    width: 150,
    offset: {
      x: 36,
      y: -8
    }
  };
  function initMessages(layer) {
    const self = this;
    self.messages = [];
    for (let i = 0; i < self.globalData.playerCount; ++i) {
      self.messages[i] = [];
      const messageGroup = new PIXI.Container();
      for (let k = 0; k < 10; ++k) {
        const messageContainer = new PIXI.Container();
        const baseScale = 0.5699481865284974;
        const bubble = new PIXI.Container();
        const bubbleLeft = PIXI.Sprite.from("dial_side.png");
        const bubbleRight = PIXI.Sprite.from("dial_side.png");
        const bubbleMid = PIXI.Sprite.from("dial_mid.png");
        const bubbleArrow = PIXI.Sprite.from("dial_arrow.png");
        bubbleLeft.anchor.y = 0.5;
        bubbleRight.anchor.y = 0.5;
        bubbleMid.anchor.y = 0.5;
        bubbleLeft.scale.set(-baseScale, baseScale);
        bubbleRight.scale.set(baseScale, baseScale);
        bubbleMid.scale.set(baseScale, baseScale);
        bubbleArrow.scale.set(baseScale, baseScale);
        bubble.y = -18;
        bubbleArrow.y = bubbleMid.height / 2 - 5;
        bubbleArrow.x = -25;
        bubble.addChild(bubbleLeft);
        bubble.addChild(bubbleRight);
        bubble.addChild(bubbleMid);
        bubble.addChild(bubbleArrow);
        const textStyle = {
          fontFamily: "Arial",
          fontWeight: "700",
          fontSize: 46,
          fill: self.globalData.players[i].color,
          align: "center",
          wordWrap: true,
          wordWrapWidth: 90
        };
        const messageText = new PIXI.Text("", textStyle);
        messageText.anchor.x = 0.5;
        messageText.anchor.y = 0.5;
        messageText.y = -20;
        flagForDestructionOnReinit(messageText);
        messageContainer.messageText = messageText;
        messageContainer.updateText = (text, x, y) => {
          bubbleArrow.visible = false;
          bubble.visible = !!text;
          messageText.text = text;
          const maxHeight = 150;
          if (messageText.height > maxHeight) {
            while (messageText.text.length > 3 && messageText.height > maxHeight) {
              messageText.text = messageText.text.slice(0, -4) + "...";
            }
          }
          const w = messageText.width;
          bubbleLeft.x = -w / 2;
          bubbleRight.x = w / 2;
          bubbleMid.x = -w / 2;
          bubbleMid.width = w;
          messageContainer.position.set(x, y);
          messageContainer.y += messageBox.offset.y * messageText.height / 16;
          messageContainer.x += messageBox.offset.x + messageContainer.width / 2;
          bubble.height = messageText.height * 1.2;
          bubbleArrow.x = -messageContainer.width / 2;
          bubbleArrow.visible = true;
          if (messageContainer.x > WIDTH - messageContainer.width / 2) {
            const diff = messageContainer.x - (WIDTH - messageContainer.width / 2);
            messageContainer.x -= diff;
            bubbleArrow.x += diff;
          }
          if (messageText.height > 50) {
            bubble.y = -18;
            messageText.y = -20;
          } else {
            bubble.y = 0;
            messageText.y = 0;
          }
        };
        messageContainer.addChild(bubble);
        messageContainer.addChild(messageText);
        self.messages[i].push(messageContainer);
        messageGroup.addChild(messageContainer);
      }
      layer.addChild(messageGroup);
    }
  }

  // ts/graphics/ViewModule.ts
  var api = {
    setDebugMode: (value) => {
      api.options.debugMode = value;
    },
    options: {
      debugMode: false,
      showOthersMessages: true,
      showMyMessages: true,
      meInGame: false
    }
  };
  var ViewModule = class {
    constructor() {
      window.debug = this;
      this.states = [];
      this.pool = {};
      this.time = 0;
      this.tooltipManager = new TooltipManager();
      this.api = api;
      this.api.setDebugMode = (value) => {
        this.api.options.debugMode = value;
        const parent = this.container?.parent;
        if (parent && parent.children && parent.children.length > 1) {
          parent.children[1].visible = !value;
        }
      };
    }
    static get moduleName() {
      return "graphics";
    }
    registerTooltip(container, getString) {
      container.interactive = true;
      this.tooltipManager.register(container, getString);
    }
    // Effects
    getFromPool(type) {
      if (!this.pool[type]) {
        this.pool[type] = [];
      }
      for (const e2 of this.pool[type]) {
        if (!e2.busy) {
          e2.busy = true;
          e2.display.visible = true;
          return e2;
        }
      }
      const e = this.createEffect(type);
      this.pool[type].push(e);
      e.busy = true;
      return e;
    }
    createEffect(type) {
      let display = null;
      const organAnimationKey = Object.keys(ORGANS_ANIMATIONS_VALUES).find((k) => type.startsWith(k));
      if (type.startsWith("particle")) {
        const idx = parseInt(type.slice(8));
        display = PIXI.Sprite.from(SPORE_PARTICLES[idx]);
        display.anchor.set(0.5);
        this.sporeLayer.addChild(display);
      } else if (type === "tail") {
        display = this.initTail();
        this.tailLayer.addChild(display);
      } else if (organAnimationKey != null) {
        const idx = parseInt(type.slice(organAnimationKey.length));
        const values = ORGANS_ANIMATIONS_VALUES[organAnimationKey];
        display = PIXI.AnimatedSprite.fromFrames(values.frames[idx]);
        display.loop = false;
        display.gotoAndStop(0);
        display.anchor.copyFrom(values.anchors ?? { x: 0.5, y: 0.5 });
        this.layersMap[organAnimationKey].addChild(display);
      } else if (type === "absorb") {
        display = PIXI.AnimatedSprite.fromFrames(ABORPTION_FRAMES);
        display.anchor.copyFrom(ABSORPTION_ANCHOR);
        this.absorptionLayer.addChild(display);
      } else if (type === "wall") {
        display = PIXI.AnimatedSprite.fromFrames(WALL_SPAWN_FRAMES);
        display.anchor.copyFrom(WALL_SPAWN_ANCHOR);
        this.wallSpawnLayer.addChild(display);
      } else {
        console.error("Unknown effect type", type);
      }
      return { busy: false, display };
    }
    updateScene(previousData, currentData, progress, playerSpeed) {
      const frameChange = this.currentData !== currentData;
      const fullProgressChange = this.progress === 1 !== (progress === 1);
      this.previousData = previousData;
      this.currentData = currentData;
      this.progress = progress;
      this.playerSpeed = playerSpeed || 0;
      this.resetEffects();
      this.updateOrgans();
      this.updateHud();
      this.updateGrid();
      this.updateMovables();
      const parent = this.container.parent;
      if (parent && parent.children && parent.children.length > 1) {
        parent.children[1].visible = !this.api.options.debugMode;
      }
    }
    updateHud() {
      const currentData = this.currentData;
      for (let player of this.globalData.players) {
        const { score, proteins } = this.huds[player.index];
        for (let i = 0; i < 4; ++i) {
          proteins[i].text = currentData.storage[player.index][i].toString();
        }
        score.text = currentData.organs[player.index].length.toString();
      }
    }
    getAnimProgress({ start, end }, progress) {
      return unlerp(start, end, progress);
    }
    animateSpawn(event) {
      const p = this.getAnimProgress(event.animData, this.progress);
      if (p <= 0) {
        return;
      }
      const animation = this.getFromPool(`growth${event.playerIdx}`);
      this.placeInGameZone(animation.display, event.target);
      const growthEndP = 0.3;
      const scaleStartP = 0.25;
      const fadeInEndP = 0.3;
      const growthScaleEndP = 0.4;
      const growthP = unlerp(0, growthEndP, p);
      const scaleP = unlerp(scaleStartP, 1, p);
      const growthScaleP = unlerp(growthEndP, growthScaleEndP, p);
      setAnimationProgress(animation.display, growthP);
      animation.display.scale.set(1 - growthScaleP);
      const scale = this.easeOutElastic(scaleP);
      const alpha = unlerp(scaleStartP, fadeInEndP, p);
      const organ = this.organByTileIdx[this.getTileIdx(event.target)];
      if (!organ) {
        return;
      }
      this.updateOrgan(organ, {
        scale,
        alpha,
        organData: {
          playerIdx: event.playerIdx,
          id: event.id,
          type: event.organType,
          direction: event.direction,
          pos: event.target
        }
      });
    }
    animateGrow(event) {
      const p = this.getAnimProgress(event.animData, this.progress);
      if (p <= 0) {
        return;
      }
      this.animateSpawn(event);
      const organ = this.organByTileIdx[this.getTileIdx(event.target)];
      if (!organ) {
        return;
      }
      this.updateOrganTail(organ.tail, event.target, event.coord, easeOut(p), event.playerIdx);
    }
    animateCrash(event) {
      const p = this.getAnimProgress(event.animData, this.progress);
      if (p <= 0) {
        return;
      }
      const tileIdx = this.getTileIdx(event.coord);
      const tile = this.tiles[tileIdx];
      if (p < 1) {
        const animation = this.getFromPool("wall");
        this.placeInGameZone(animation.display, event.coord);
        setAnimationProgress(animation.display, p);
        const scale = this.tileSize / 178;
        animation.display.scale.set(scale);
        tile.wall.visible = false;
      } else {
        tile.wall.visible = true;
      }
      tile.protein.alpha = 1 - p;
      const growFrom = event.coords.slice(1);
      for (const coord of growFrom) {
        const fakeTail = this.getFromPool("tail");
        const fromOrgan = this.currentData.organByTileIdx[this.getTileIdx(coord)] ?? this.previousData.organByTileIdx[this.getTileIdx(coord)];
        const alpha = 1 - unlerp(0.9, 1, p);
        this.updateOrganTail(fakeTail.display, event.coord, coord, easeOut(p), fromOrgan.playerIdx ?? 0, alpha);
      }
    }
    animateAbsorb(event) {
      const p = this.getAnimProgress(event.animData, this.progress);
      if (p <= 0) {
        return;
      }
      const tileIdx = this.getTileIdx(event.coord);
      const tile = this.tiles[tileIdx];
      const fadeP = unlerp(0.1, 0.6, p);
      tile.protein.alpha = 1 - fadeP;
      if (p >= 1) {
        return;
      }
      const startP = 0.25;
      const animation = this.getFromPool("absorb");
      animation.display.scale.set(this.organScale * 1.5);
      this.placeInGameZone(animation.display, event.coord);
      const absP = unlerp(startP, 1, p);
      setAnimationProgress(animation.display, absP);
      if (p < startP) {
        animation.display.visible = false;
      }
      this.animateRoot(event.coord, "HARVEST", event.playerIdx);
    }
    animateSpore(event) {
      const p = this.getAnimProgress(event.animData, this.progress);
      if (p <= 0 || p >= 1) {
        return;
      }
      const particleAnimStartP = 0.2;
      const sportAnimEndP = 0.5;
      if (p <= sportAnimEndP) {
        const organ = this.organByTileIdx[this.getTileIdx(event.coord)];
        if (!organ) {
          return;
        }
        organ.sprite.visible = false;
        const sporeAnimP = unlerp(0, sportAnimEndP, p);
        const animation = this.getFromPool(`spore${event.playerIdx}`);
        animation.display.scale.set(this.organScale);
        const direction = this.getCardinalDirectionBetween(event.coord, event.target);
        animation.display.rotation = ROTATIONS_MAP[direction];
        this.placeInGameZone(animation.display, event.coord);
        setAnimationProgress(animation.display, sporeAnimP);
      }
      if (p >= particleAnimStartP) {
        const particleAnimP = unlerp(particleAnimStartP, 1, p);
        const fx = this.getFromPool(`particle${event.playerIdx}`);
        const direction = this.getCardinalDirectionBetween(event.coord, event.target);
        fx.display.rotation = ROTATIONS_MAP[direction];
        const from = event.coord;
        const to = event.target;
        this.placeInGameZone(fx.display, lerpPosition(from, to, particleAnimP));
      }
    }
    animateHarvest(event) {
      const p = this.getAnimProgress(event.animData, this.progress);
      if (p <= 0 || p >= 1) {
        return;
      }
      const organ = this.organByTileIdx[this.getTileIdx(event.coord)];
      if (!organ) {
        return;
      }
      const animation = this.getFromPool(`harvest${event.playerIdx}`);
      animation.display.scale.set(this.organScale);
      const direction = this.getCardinalDirectionBetween(event.coord, event.target);
      animation.display.rotation = ROTATIONS_MAP[direction];
      this.placeInGameZone(animation.display, event.coord);
      setAnimationProgress(animation.display, p);
      this.updateOrgan(organ, {
        organData: {
          playerIdx: event.playerIdx,
          id: event.id,
          type: "HARVESTER",
          direction: this.getCardinalDirectionBetween(event.coord, event.target),
          pos: event.coord
        }
      });
    }
    animateAttack(event) {
      const p = this.getAnimProgress(event.animData, this.progress);
      if (p <= 0 || p >= 1) {
        return;
      }
      const organ = this.organByTileIdx[this.getTileIdx(event.coord)];
      if (!organ) {
        return;
      }
      organ.sprite.visible = false;
      const animation = this.getFromPool(`attack${event.playerIdx}`);
      animation.display.scale.set(this.organScale);
      const direction = this.getCardinalDirectionBetween(event.coord, event.target);
      animation.display.rotation = ROTATIONS_MAP[direction];
      this.placeInGameZone(animation.display, event.coord);
      setAnimationProgress(animation.display, p);
      this.animateRoot(event.coord, "ATTACK", event.playerIdx);
    }
    animateRoot(fromCoord, state, playerIdx) {
      const rootTileIdx = this.currentData.rootTileIdxByTileIdx[this.getTileIdx(fromCoord)];
      const root = this.currentData.organByTileIdx[rootTileIdx];
      if (root == null) {
        return;
      }
      const displayRoot = this.organByTileIdx[rootTileIdx];
      if (!displayRoot) {
        return;
      }
      const sprite = displayRoot.sprite;
      sprite.texture = PIXI.Texture.from(ROOT_STATES[playerIdx][state]);
    }
    getCardinalDirectionBetween(a, b) {
      const dx = b.x - a.x;
      const dy = b.y - a.y;
      if (Math.abs(dx) > Math.abs(dy)) {
        return dx > 0 ? "E" : "W";
      } else {
        return dy > 0 ? "S" : "N";
      }
    }
    animateDeath(event) {
      const p = this.getAnimProgress(event.animData, this.progress);
      if (p <= 0) {
        return;
      }
      const animation = this.getFromPool(`death${event.playerIdx}`);
      animation.display.scale.set(this.organScale);
      this.placeInGameZone(animation.display, event.coord);
      const poofStartP = 0.1;
      const scaleEndP = 0.1;
      const poofP = unlerp(poofStartP, 1, p);
      setAnimationProgress(animation.display, poofP);
      if (p < poofStartP || p >= 1) {
        animation.display.visible = false;
      }
      const scale = lerp(1, 0.8, unlerp(0, scaleEndP, p));
      const alpha = p > 0.11 ? 0 : 1;
      const organ = this.organByTileIdx[this.getTileIdx(event.coord)];
      if (!organ) {
        return;
      }
      this.updateOrgan(organ, {
        scale,
        alpha,
        organData: {
          playerIdx: event.playerIdx,
          id: event.id,
          type: event.organType,
          direction: event.direction,
          pos: event.coord
        }
      });
      organ.tail.alpha = lerp(0.7, 0, unlerp(0, scaleEndP, p));
      this.animateRoot(event.coord, "DEATH", event.playerIdx);
    }
    updateOrganTail(tail, target, from, progress, pIdx, alpha = 1) {
      if (progress <= 0) {
        return;
      }
      tail.visible = true;
      tail.alpha = 0.7 * alpha;
      const parentPos = this.toBoardPos(from);
      const childPos = this.toBoardPos(target);
      const angle = Math.atan2(childPos.y - parentPos.y, childPos.x - parentPos.x);
      const tileOffsetToWall = this.tileSize / 2 / 5 * 4;
      tail.position.set(parentPos.x + this.tileSizeWithGrid / 2, parentPos.y + this.tileSizeWithGrid / 2);
      const direction = this.getCardinalDirectionBetween(from, target);
      if (direction === "N") {
        tail.position.y -= tileOffsetToWall;
      } else if (direction === "S") {
        tail.position.y += tileOffsetToWall;
      }
      if (direction === "E") {
        tail.position.x += tileOffsetToWall;
      } else if (direction === "W") {
        tail.position.x -= tileOffsetToWall;
      }
      tail.rotation = angle;
      const finalWidth = (this.tileSize / 2 - tileOffsetToWall) * 2;
      tail.width = finalWidth * progress;
      tail.height = this.tileSizeWithGrid / 3;
      tail.texture = PIXI.Texture.from(pIdx === 0 ? "MurOrange" : "MurBleu");
    }
    updateOrgan(organ, { organData, scale, zIndex, alpha, rotation }) {
      const { sprite, container } = organ;
      if (organData != null) {
        container.rotation = ROTATIONS_MAP[organData.direction];
        if (organData.type === "ROOT") {
          container.rotation += Math.PI / 2;
        }
        if (organData.playerIdx != null) {
          const organType = organData.type;
          const spriteName = ORGANS[organData.playerIdx][organType];
          sprite.texture = PIXI.Texture.from(spriteName);
          sprite.anchor.copyFrom(ORGAN_ANCHORS[organType]);
        }
      }
      if (scale != null) {
        container.scale.set(scale);
      }
      if (zIndex != null) {
        sprite.zIndex = zIndex;
      }
      if (alpha != null) {
        sprite.alpha = alpha;
      }
      if (rotation != null) {
        container.rotation += rotation;
      }
      sprite.visible = true;
      return organ;
    }
    placeInGameZone(display, coord) {
      const pos = this.toBoardPos(coord);
      display.position.set(pos.x + this.tileSizeWithGrid / 2, pos.y + this.tileSizeWithGrid / 2);
    }
    updateOrgans() {
      for (const organ of this.organs) {
        this.updateOrgan(organ, { alpha: 1, rotation: 0, scale: 1, zIndex: 0 });
        organ.sprite.visible = false;
        organ.tail.visible = false;
      }
      for (const message of this.messages.flat()) {
        message.updateText("", 0, 0);
      }
      const currentData = this.currentData;
      const grows = currentData.events.filter((e) => e.type === events_default.GROW);
      const deaths = currentData.events.filter((e) => e.type === events_default.DEATH);
      const attacks = currentData.events.filter((e) => e.type === events_default.ATTACK);
      const harvests = currentData.events.filter((e) => e.type === events_default.HARVEST);
      const spores = currentData.events.filter((e) => e.type === events_default.SPORE);
      const spawns = currentData.events.filter((e) => e.type === events_default.SPAWN_ROOT);
      let nucleusIdx = [0, 0];
      for (let pIdx = 0; pIdx < this.globalData.playerCount; ++pIdx) {
        const player = this.globalData.players[pIdx];
        const data = this.progress < 1 ? this.previousData : currentData;
        for (const organData of data.organs[pIdx]) {
          const tileIdx = this.getTileIdx(organData.pos);
          const organ = this.organByTileIdx[tileIdx];
          if (!organ) {
            continue;
          }
          this.updateOrgan(organ, { organData });
          if (organData.parentId != null && organData.parentId != 0) {
            const parentData = data.organById[organData.parentId];
            if (!parentData) {
              continue;
            }
            this.updateOrganTail(organ.tail, organData.pos, parentData.pos, 1, pIdx);
          } else {
            organ.tail.visible = false;
            const text = currentData.messages[pIdx][organData.id] ?? "";
            if (text !== "") {
              const messageIdx = Math.min(this.messages[0].length - 1, nucleusIdx[player.index]++);
              const message = this.messages[player.index][messageIdx];
              const boardPos = this.toBoardPos(organData.pos);
              let globalPoint = this.gameZone.toGlobal(boardPos);
              let containerPoint = this.container.toLocal(globalPoint);
              message.updateText(text, containerPoint.x, containerPoint.y);
            }
          }
        }
      }
      for (const event of grows) {
        this.animateGrow(event);
      }
      for (const event of spawns) {
        event.target = event.coord;
        event.organType = "ROOT";
        this.animateSpawn(event);
      }
      for (const event of attacks) {
        this.animateAttack(event);
      }
      for (const event of deaths) {
        this.animateDeath(event);
      }
      for (const event of harvests) {
        this.animateHarvest(event);
      }
      for (const event of spores) {
        this.animateSpore(event);
      }
    }
    getTileIdx(coord) {
      return coord.y * this.globalData.width + coord.x;
    }
    fromTileIdx(tileIdx) {
      return {
        x: tileIdx % this.globalData.width,
        y: Math.floor(tileIdx / this.globalData.width)
      };
    }
    toBoardPos(coord) {
      return {
        x: coord.x * this.tileSizeWithGrid,
        y: coord.y * this.tileSizeWithGrid
      };
    }
    upThenDown(t) {
      return Math.min(1, bell(t) * 2);
    }
    updateMovables() {
      for (const m of this.movables) {
        const prev = m.getPos(this.previousData);
        const cur = m.getPos(this.currentData);
        let visible = true;
        let alpha = 1;
        if (prev && cur) {
          const pos = lerpPosition(prev, cur, this.progress);
          m.entity.position.copyFrom(pos);
        } else if (prev) {
          m.entity.position.copyFrom(prev);
          alpha = 1 - this.progress;
        } else if (cur) {
          m.entity.position.copyFrom(cur);
          alpha = this.progress;
        } else {
          visible = false;
        }
        m.entity.visible = visible;
        m.entity.alpha = alpha;
      }
    }
    resetEffects() {
      for (const type in this.pool) {
        for (const effect of this.pool[type]) {
          effect.display.visible = false;
          effect.busy = false;
        }
      }
    }
    animateScene(delta) {
      this.time += delta;
      for (const player of this.globalData.players) {
        for (let i = 0; i < 10; ++i) {
          const message = this.messages[player.index][i];
          renderMessageContainer.bind(this)(message, player.index, delta);
        }
      }
    }
    asLayer(func) {
      const layer = new PIXI.Container();
      func.bind(this)(layer);
      return layer;
    }
    reinitScene(container, canvasData) {
      this.time = 0;
      this.oversampling = canvasData.oversampling;
      this.container = container;
      this.pool = {};
      this.canvasData = canvasData;
      this.movables = [];
      this.tileSizeWithGrid = Math.min(GAME_ZONE_RECT.w / this.globalData.width, GAME_ZONE_RECT.h / this.globalData.height);
      this.tileSize = this.tileSizeWithGrid - GRID_LINE_WIDTH;
      this.organSize = this.tileSize - ORGAN_TILE_PADDING * 2;
      this.sporeLayer = new PIXI.Container();
      this.tailLayer = new PIXI.Container();
      this.growthLayer = new PIXI.Container();
      this.harvestLayer = new PIXI.Container();
      this.organLayer = this.asLayer(this.initOrgans);
      const messageLayer = this.asLayer(initMessages);
      this.attackLayer = new PIXI.Container();
      this.absorptionLayer = new PIXI.Container();
      this.wallSpawnLayer = new PIXI.Container();
      this.layersMap = {
        growth: this.growthLayer,
        harvest: this.harvestLayer,
        spore: this.sporeLayer,
        death: this.organLayer,
        attack: this.attackLayer
      };
      const tooltipLayer = this.tooltipManager.reinit();
      tooltipLayer.interactiveChildren = false;
      const gameZone = new PIXI.Container();
      const background = PIXI.Sprite.from("Background_2.jpg");
      const grid = this.asLayer(this.initGrid);
      const hud = this.asLayer(this.initHud);
      gameZone.addChild(grid);
      gameZone.addChild(this.tailLayer);
      gameZone.addChild(this.wallLayer);
      gameZone.addChild(this.wallSpawnLayer);
      gameZone.addChild(this.growthLayer);
      gameZone.addChild(this.sporeLayer);
      gameZone.addChild(this.organLayer);
      gameZone.addChild(this.harvestLayer);
      gameZone.addChild(this.attackLayer);
      gameZone.addChild(this.absorptionLayer);
      gameZone.x = GAME_ZONE_RECT.x;
      gameZone.y = GAME_ZONE_RECT.y;
      const gameWidth = this.globalData.width * this.tileSizeWithGrid;
      const gameHeight = this.globalData.height * this.tileSizeWithGrid;
      gameZone.x += (GAME_ZONE_RECT.w - gameWidth) / 2;
      gameZone.y += (GAME_ZONE_RECT.h - gameHeight) / 2;
      this.gameZone = gameZone;
      container.addChild(background);
      container.addChild(gameZone);
      container.addChild(hud);
      container.addChild(messageLayer);
      container.addChild(tooltipLayer);
      container.interactive = true;
      container.on("mousemove", (event) => {
        this.tooltipManager.moveTooltip(event);
      });
      hud.interactiveChildren = false;
      this.tooltipManager.registerGlobal((data) => {
        const pos = data.getLocalPosition(gameZone);
        const x = Math.floor(pos.x / this.tileSizeWithGrid);
        const y = Math.floor(pos.y / this.tileSizeWithGrid);
        if (x < 0 || x >= this.globalData.width || y < 0 || y >= this.globalData.height) {
          return null;
        }
        const blocks = [];
        const tile = this.currentData.tiles[y * this.globalData.width + x];
        if (tile.organ != null) {
          blocks.push(`Organ ${tile.organ.id}
${tile.organ.type} ${tile.organ.direction}`);
        }
        blocks.push(`(${x}, ${y})`);
        return blocks.join("\n--------\n");
      });
    }
    placeInHUD(element, { x, y, w, h }, pIdx) {
      fit(element, w, h);
      element.position.set(pIdx ? WIDTH - 1 - x : x, y);
      element.anchor.set(pIdx ? 1 : 0, 0);
    }
    initHud(layer) {
      const background = PIXI.Sprite.from("HUD.png");
      layer.addChild(background);
      this.huds = [];
      for (const player of this.globalData.players) {
        const avatar = PIXI.Sprite.from(player.avatar);
        const name = new PIXI.Text(player.name, {
          fontSize: "48px",
          fill: HUD_COLORS[player.index],
          fontWeight: "bold"
        });
        const score = new PIXI.Text("0", {
          fontSize: "48px",
          fill: HUD_COLORS[player.index],
          fontWeight: "bold"
        });
        this.placeInHUD(avatar, AVATAR_RECT, player.index);
        this.placeInHUD(name, NAME_RECT, player.index);
        this.placeInHUD(score, SCORE_RECT, player.index);
        const proteins = [];
        for (let i = 0; i < 4; ++i) {
          const x = i * PROTEIN_SEP + PROTEIN_RECT.x;
          const protein = new PIXI.Text("0", {
            fontSize: "48px",
            fill: HUD_COLORS[player.index],
            fontWeight: "bold"
          });
          this.placeInHUD(protein, { ...PROTEIN_RECT, x }, player.index);
          layer.addChild(protein);
          proteins.push(protein);
        }
        layer.addChild(avatar, name, score);
        if (player.index === 1) {
          avatar.x -= 2;
          avatar.y += 2;
          proteins.reverse();
        }
        this.huds.push({ avatar, name, score, proteins });
      }
    }
    initTail() {
      const tail = PIXI.Sprite.from("MurOrange");
      tail.anchor.set(0, 0.5);
      return tail;
    }
    initOrgans(layer) {
      this.organByTileIdx = {};
      this.organs = [];
      for (const tileIdx of this.globalData.tileIdxInNeedOfOrgan) {
        const sprite = PIXI.Sprite.from(ORGANS[0].ROOT);
        const tail = this.initTail();
        sprite.anchor.copyFrom(ORGAN_ANCHORS.ROOT);
        fit(sprite, this.organSize, this.organSize);
        this.organScale = sprite.scale.x;
        const container = new PIXI.Container();
        const organ = { sprite, tail, container };
        this.organByTileIdx[tileIdx] = organ;
        this.organs.push(organ);
        this.placeInGameZone(container, this.fromTileIdx(tileIdx));
        container.addChild(sprite);
        layer.addChild(container);
        this.tailLayer.addChild(tail);
      }
    }
    initGrid(layer) {
      this.tiles = [];
      this.wallLayer = new PIXI.Container();
      const gridLines = new PIXI.Graphics();
      gridLines.lineStyle(GRID_LINE_WIDTH, 0, 1);
      gridLines.x = GRID_LINE_WIDTH;
      gridLines.y = GRID_LINE_WIDTH;
      for (let y = 0; y <= this.globalData.height; ++y) {
        gridLines.moveTo(0, y * this.tileSizeWithGrid);
        gridLines.lineTo(this.globalData.width * this.tileSizeWithGrid, y * this.tileSizeWithGrid);
      }
      for (let x = 0; x <= this.globalData.width; ++x) {
        gridLines.moveTo(x * this.tileSizeWithGrid, 0);
        gridLines.lineTo(x * this.tileSizeWithGrid, this.globalData.height * this.tileSizeWithGrid);
      }
      const texture = PIXI.RenderTexture.create({ width: WIDTH, height: HEIGHT });
      flagForDestructionOnReinit(texture);
      getRenderer().render(gridLines, texture);
      const gridLineSprite = new PIXI.Sprite(texture);
      gridLineSprite.alpha = 0.2;
      gridLineSprite.position.set(-GRID_LINE_WIDTH - 1, -GRID_LINE_WIDTH - 1);
      layer.addChild(gridLineSprite);
      for (let y = 0; y < this.globalData.height; ++y) {
        for (let x = 0; x < this.globalData.width; ++x) {
          const tileContainer = new PIXI.Container();
          tileContainer.x = this.tileSizeWithGrid * x;
          tileContainer.y = this.tileSizeWithGrid * y;
          const wall = PIXI.Sprite.from("Mur_2");
          wall.width = this.tileSize;
          wall.height = this.tileSize;
          const protein = PIXI.Sprite.from("Prot_A");
          fit(protein, this.tileSize, this.tileSize);
          protein.visible = false;
          protein.anchor.set(0.5);
          protein.position.set(this.tileSizeWithGrid / 2, this.tileSizeWithGrid / 2);
          tileContainer.addChild(wall);
          tileContainer.addChild(protein);
          this.tiles.push({ wall, protein });
          this.wallLayer.addChild(tileContainer);
        }
      }
    }
    updateGrid() {
      let tileIdx = 0;
      const data = this.progress < 1 ? this.previousData : this.currentData;
      for (let y = 0; y < this.globalData.height; ++y) {
        for (let x = 0; x < this.globalData.width; ++x) {
          const tileData = data.tiles[tileIdx];
          const tile = this.tiles[tileIdx];
          tileIdx++;
          tile.wall.visible = tileData.obstacle;
          tile.wall.alpha = 1;
          tile.protein.alpha = 1;
          if (tileData.protein === "X") {
            tile.protein.visible = false;
          } else {
            tile.protein.texture = PIXI.Texture.from(`Prot_${tileData.protein}`);
            tile.protein.visible = true;
          }
        }
      }
      const crashes = this.currentData.events.filter((e) => e.type === events_default.CRASH);
      const absorbs = this.currentData.events.filter((e) => e.type === events_default.ABSORB);
      for (const crash of crashes) {
        this.animateCrash(crash);
      }
      for (const absorb of absorbs) {
        this.animateAbsorb(absorb);
      }
    }
    easeOutElastic(x) {
      const c4 = 2 * Math.PI / 3;
      return x === 0 ? 0 : x === 1 ? 1 : Math.pow(2, -10 * x) * Math.sin((x * 10 - 0.75) * c4) + 1;
    }
    handleGlobalData(players, raw) {
      const globalData = parseGlobalData(raw);
      api.options.meInGame = !!players.find((p) => p.isMe);
      this.globalData = {
        ...globalData,
        players,
        playerCount: players.length,
        tileIdxInNeedOfOrgan: /* @__PURE__ */ new Set()
      };
    }
    handleFrameData(frameInfo, raw) {
      const dto = parseData(raw, this.globalData);
      const prev = last(this.states);
      const lastFrameOrgans = prev ? prev.organs : this.globalData.organs;
      const organById = lastFrameOrgans.flat().reduce((acc, organ) => {
        return { ...acc, [organ.id]: organ };
      }, {});
      const organByTileIdx = lastFrameOrgans.flat().reduce((acc, organ) => {
        const tileIdx = this.getTileIdx(organ.pos);
        return { ...acc, [tileIdx]: organ };
      }, {});
      const rootTileIdxByTileIdx = {};
      for (const organ of lastFrameOrgans.flat()) {
        const tileIdx = this.getTileIdx(organ.pos);
        if (tileIdx in rootTileIdxByTileIdx) {
          continue;
        }
        if (organ.type === "ROOT") {
          rootTileIdxByTileIdx[tileIdx] = tileIdx;
          continue;
        }
        let root = organ;
        while (root.parentId != null && root.parentId != 0) {
          root = organById[root.parentId];
        }
        rootTileIdxByTileIdx[tileIdx] = this.getTileIdx(root.pos);
      }
      let tiles;
      if (!prev) {
        tiles = this.globalData.tiles.map((t, idx) => ({ ...t, organ: organByTileIdx[idx] }));
      } else {
        tiles = prev.tiles.map((t, idx) => ({ ...t, organ: organByTileIdx[idx] }));
      }
      if (!prev) {
        for (const organ of lastFrameOrgans.flat()) {
          const tileIdx = this.getTileIdx(organ.pos);
          this.globalData.tileIdxInNeedOfOrgan.add(tileIdx);
        }
      }
      for (const coord of dto.events.map((e) => e.coords).flat()) {
        const tileIdx = this.getTileIdx(coord);
        this.globalData.tileIdxInNeedOfOrgan.add(tileIdx);
      }
      const eventMapPerPlayer = [{}, {}];
      const maxEventEnd = dto.events.reduce((m, e) => Math.max(m, e.animData.end), 0);
      const frameAnimDuration = Math.max(frameInfo.frameDuration, maxEventEnd, 1);
      for (const event of dto.events) {
        if (eventMapPerPlayer[event.playerIdx][event.type] == null) {
          eventMapPerPlayer[event.playerIdx][event.type] = [];
        }
        const eventMap = eventMapPerPlayer[event.playerIdx][event.type];
        eventMap.push(event);
        const updateTiles = (coord, protein, obstacle, organ) => {
          const tileIdx = this.getTileIdx(coord);
          tiles = [...tiles];
          tiles[tileIdx] = { protein, obstacle, organ };
          if (organ != null) {
            organById[organ.id] = organ;
            organByTileIdx[tileIdx] = organ;
          } else {
            const curOrgan = organByTileIdx[tileIdx];
            if (curOrgan != null) {
              delete organById[curOrgan.id];
              delete organByTileIdx[tileIdx];
            }
          }
        };
        if (event.type === events_default.CRASH) {
          updateTiles(event.coord, "X", true, null);
        } else if (event.type === events_default.GROW) {
          const newOrgan = {
            id: event.id,
            pos: event.target,
            type: event.organType,
            direction: event.direction,
            parentId: organByTileIdx[this.getTileIdx(event.coord)].id,
            playerIdx: event.playerIdx
          };
          rootTileIdxByTileIdx[this.getTileIdx(event.target)] = rootTileIdxByTileIdx[this.getTileIdx(event.coord)];
          updateTiles(event.target, "X", false, newOrgan);
        } else if (event.type === events_default.SPAWN_ROOT) {
          const newOrgan = {
            id: event.id,
            pos: event.coord,
            type: "ROOT",
            direction: event.direction,
            playerIdx: event.playerIdx
          };
          rootTileIdxByTileIdx[this.getTileIdx(event.coord)] = this.getTileIdx(event.coord);
          updateTiles(event.coord, "X", false, newOrgan);
        } else if (event.type === events_default.DEATH) {
          updateTiles(event.coord, "X", false, null);
        }
        event.animData.start /= frameAnimDuration;
        event.animData.end /= frameAnimDuration;
      }
      const organs = [[], []];
      Object.values(organById).forEach((organ) => {
        organs[organ.playerIdx].push(organ);
      });
      const frameData = {
        ...dto,
        ...frameInfo,
        tiles,
        organById,
        organByTileIdx,
        organs,
        previous: null,
        rootTileIdxByTileIdx
      };
      frameData.previous = last(this.states) ?? frameData;
      this.states.push(frameData);
      return frameData;
    }
  };
  return __toCommonJS(main_exports);
})();
