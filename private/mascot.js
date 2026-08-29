/*  Cherry Mascot — rigged glTF character
 *  ------------------------------------------------------------------
 *  Loads the Blender-authored cherry (skinned armature + 11 facial
 *  morph targets) and drives it from the agent's conversation state.
 *
 *  Public API (window.CherryMascot):
 *      .idle()  .thinking()  .talking()  .jump()  .error()
 *      .wave()  .happy()     .sad()      .sleep()
 *      .setState(name)          -> any of the above state names
 *      .play(clipName, opts)    -> raw clip access
 *      .look(x, y)              -> -1..1 eye aim
 *      .clips                   -> available clip names
 */

// NOTE: resolved through the <script type="importmap"> in index.html.
import * as THREE from "three";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import { DRACOLoader } from "three/addons/loaders/DRACOLoader.js";

const MODEL_URL   = "/static/models/cherry.glb";
const DRACO_PATH  = "https://unpkg.com/three@0.160.0/examples/jsm/libs/draco/gltf/";

/* ---------------------------------------------------------------- states */
const STATES = {
    IDLE:     "idle",
    THINKING: "thinking",
    TALKING:  "talking",
    JUMPING:  "jumping",
    SLEEPING: "sleeping",
    ERROR:    "error",
    WAVING:   "waving",
    HAPPY:    "happy",
    SAD:      "sad"
};

// state -> { clip, loop, next }  ("next" auto-returns once the clip ends)
const STATE_CLIP = {
    [STATES.IDLE]:     { clip: "idle",     loop: true  },
    [STATES.THINKING]: { clip: "thinking", loop: true  },
    [STATES.TALKING]:  { clip: "talking",  loop: true  },
    [STATES.SLEEPING]: { clip: "sleep",    loop: true  },
    [STATES.SAD]:      { clip: "sad",      loop: true  },
    [STATES.JUMPING]:  { clip: "happy",    loop: false, next: STATES.IDLE },
    [STATES.HAPPY]:    { clip: "happy",    loop: false, next: STATES.IDLE },
    [STATES.WAVING]:   { clip: "wave",     loop: false, next: STATES.IDLE },
    [STATES.ERROR]:    { clip: "sad",      loop: false, next: STATES.IDLE }
};

/* ------------------------------------------------------ material recipes */
// Which exported Blender material is shaded how in three.js.
const FLAT_MATS = new Set([
    "M_Line", "M_Crease", "M_GreenLine", "M_Iris",
    "M_MouthInner", "M_LipFill", "M_EyeHi", "M_White"
]);
const OUTLINE_MATS = new Set(["M_OutlineGreen", "M_OutlineRed", "M_OutlineEye"]);

// 4-band toon ramp — mirrors the ColorRamp stops used in the Blender shader.
function makeGradientMap() {
    const steps = [0.50, 0.68, 0.85, 1.0];
    const data = new Uint8Array(steps.length * 4);
    steps.forEach((s, i) => {
        const v = Math.round(s * 255);
        data[i * 4] = data[i * 4 + 1] = data[i * 4 + 2] = v;
        data[i * 4 + 3] = 255;
    });
    const tex = new THREE.DataTexture(data, steps.length, 1, THREE.RGBAFormat);
    tex.minFilter = tex.magFilter = THREE.NearestFilter;
    tex.generateMipmaps = false;
    tex.needsUpdate = true;
    return tex;
}

class CherryMascotController {
    constructor(container) {
        this.container = container;
        this.state = STATES.IDLE;
        this.stateStartedAt = performance.now();
        this.lastInteractionAt = performance.now();
        this.dragging = false;
        this.pointerOffset = { x: 0, y: 0 };
        this.ready = false;
        this.clips = [];

        this.actions = {};
        this.current = null;
        this.morph = null;          // { mesh, index: {name -> i} }
        this.blinkNext = 1.5;
        this.blinkT = -1;
        this.lookTarget = new THREE.Vector2(0, 0);
        this.lookNow = new THREE.Vector2(0, 0);
        this.lookNext = 2.0;
        this.mouth = 0;
        this.autoSleepAfter = 35;   // seconds idle before dozing off

        this.scene = new THREE.Scene();
        this.camera = new THREE.PerspectiveCamera(32, 1, 0.05, 100);

        this.renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true });
        this.renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
        this.renderer.outputColorSpace = THREE.SRGBColorSpace;
        this.renderer.setClearColor(0x000000, 0);
        this.container.appendChild(this.renderer.domElement);

        this.clock = new THREE.Clock();
        this.gradientMap = makeGradientMap();

        this.root = new THREE.Group();      // holds the loaded character
        this.scene.add(this.root);

        this.createLights();
        this.bindEvents();
        this.resize();
        this.load();
        this.animate();
    }

    /* ------------------------------------------------------------ setup */
    createLights() {
        this.scene.add(new THREE.HemisphereLight(0xffffff, 0x5a3a3a, 1.05));
        const key = new THREE.DirectionalLight(0xffffff, 2.0);
        key.position.set(-2.6, 3.4, 4.2);
        this.scene.add(key);
        const fill = new THREE.DirectionalLight(0xffd9e2, 0.5);
        fill.position.set(3.2, 1.2, 2.4);
        this.scene.add(fill);
    }

    load() {
        const draco = new DRACOLoader();
        draco.setDecoderPath(DRACO_PATH);
        const loader = new GLTFLoader();
        loader.setDRACOLoader(draco);

        loader.load(
            MODEL_URL,
            (gltf) => this.onLoaded(gltf),
            undefined,
            (err) => {
                console.error("[CherryMascot] failed to load model", err);
                this.container.classList.add("mascot-failed");
            }
        );
    }

    onLoaded(gltf) {
        const model = gltf.scene;
        model.traverse((o) => {
            if (!o.isMesh) return;
            o.frustumCulled = false;                 // skinned + morphed
            o.material = this.convertMaterial(o.material);
            if (o.morphTargetDictionary && !this.morph) {
                this.morph = { mesh: o, index: o.morphTargetDictionary };
            }
        });
        this.root.add(model);
        this.frame(model);

        this.mixer = new THREE.AnimationMixer(model);
        gltf.animations.forEach((clip) => {
            const a = this.mixer.clipAction(clip);
            a.clampWhenFinished = true;
            this.actions[clip.name] = a;
            this.clips.push(clip.name);
        });
        this.mixer.addEventListener("finished", (e) => this.onClipFinished(e));

        this.ready = true;
        this.container.classList.add("mascot-ready");
        this.applyState(STATES.IDLE, 0);
    }

    convertMaterial(src) {
        const name = src.name || "";
        const color = src.color ? src.color.clone() : new THREE.Color(0xffffff);

        if (OUTLINE_MATS.has(name)) {
            // inverted hull: the shell's faces are reversed in the mesh itself,
            // so plain front-face rendering reproduces Blender's backface cull.
            return new THREE.MeshBasicMaterial({
                name, color, side: THREE.FrontSide, toneMapped: false
            });
        }
        if (FLAT_MATS.has(name)) {
            return new THREE.MeshBasicMaterial({ name, color, toneMapped: false });
        }
        return new THREE.MeshToonMaterial({
            name, color, gradientMap: this.gradientMap
        });
    }

    // centre the character and pull the camera back to fit it
    frame(model) {
        // world matrices must be current or the box collapses to the bind pose
        model.updateWorldMatrix(true, true);
        const box = new THREE.Box3().setFromObject(model);
        const size = box.getSize(new THREE.Vector3());
        const centre = box.getCenter(new THREE.Vector3());
        model.position.sub(centre);
        model.position.y += size.y * 0.02;

        const fov = THREE.MathUtils.degToRad(this.camera.fov);
        const aspect = Math.max(this.camera.aspect, 0.01);
        const fit = Math.max(size.y, size.x / aspect);
        this.modelSize = size;
        this.frameDistance = (fit / 2) / Math.tan(fov / 2) * 1.18;
        this.camera.position.set(0, 0, this.frameDistance);
        this.camera.lookAt(0, 0, 0);
        this.camera.near = this.frameDistance * 0.05;
        this.camera.far = this.frameDistance * 6;
        this.camera.updateProjectionMatrix();
    }

    /* -------------------------------------------------------- animation */
    play(clipName, { loop = true, fade = 0.28 } = {}) {
        const next = this.actions[clipName];
        if (!next) return false;
        if (this.current === next && next.isRunning()) return true;

        next.reset();
        next.setLoop(loop ? THREE.LoopRepeat : THREE.LoopOnce, loop ? Infinity : 1);
        next.enabled = true;
        next.setEffectiveTimeScale(1);
        next.setEffectiveWeight(1);

        if (this.current && this.current !== next) {
            next.crossFadeFrom(this.current, fade, false).play();
        } else {
            next.fadeIn(fade).play();
        }
        this.current = next;
        return true;
    }

    onClipFinished() {
        const spec = STATE_CLIP[this.state];
        if (spec && spec.next) this.applyState(spec.next);
    }

    applyState(name, fade = 0.28) {
        const spec = STATE_CLIP[name];
        if (!spec) return;
        this.state = name;
        this.stateStartedAt = performance.now();
        this.container.classList.toggle("is-sleeping", name === STATES.SLEEPING);
        if (this.ready) this.play(spec.clip, { loop: spec.loop, fade });
    }

    setState(name) {
        if (!STATE_CLIP[name]) return;
        this.lastInteractionAt = performance.now();
        // waking up gets a little wave instead of a hard cut
        if (this.state === STATES.SLEEPING && name === STATES.IDLE) {
            this.applyState(STATES.WAVING, 0.45);
            return;
        }
        this.applyState(name);
    }

    idle()     { this.setState(STATES.IDLE); }
    thinking() { this.setState(STATES.THINKING); }
    talking()  { this.setState(STATES.TALKING); }
    jump()     { this.setState(STATES.JUMPING); }
    happy()    { this.setState(STATES.HAPPY); }
    wave()     { this.setState(STATES.WAVING); }
    sad()      { this.setState(STATES.SAD); }
    error()    { this.setState(STATES.ERROR); }
    sleep()    { this.applyState(STATES.SLEEPING, 0.7); }

    /* ------------------------------------------------------ face driving */
    setMorph(key, value) {
        if (!this.morph) return;
        const i = this.morph.index[key];
        if (i === undefined) return;
        this.morph.mesh.morphTargetInfluences[i] = value;
    }
    getMorph(key) {
        if (!this.morph) return 0;
        const i = this.morph.index[key];
        return i === undefined ? 0 : this.morph.mesh.morphTargetInfluences[i];
    }

    look(x, y) {
        this.lookTarget.set(
            THREE.MathUtils.clamp(x, -1, 1),
            THREE.MathUtils.clamp(y, -1, 1)
        );
        this.lookNext = 1.6 + Math.random() * 2.2;
    }

    // procedural life applied *after* the mixer so it layers over the clips
    faceTick(dt, time) {
        if (!this.morph) return;
        const asleep = this.getMorph("sleep") > 0.5 || this.state === STATES.SLEEPING;

        // --- blink ---------------------------------------------------
        if (!asleep) {
            this.blinkNext -= dt;
            if (this.blinkT < 0 && this.blinkNext <= 0) {
                this.blinkT = 0;
                this.blinkNext = 2.4 + Math.random() * 3.6;
            }
            if (this.blinkT >= 0) {
                this.blinkT += dt;
                const D = 0.16;
                const p = this.blinkT / D;
                this.setMorph("blink", p < 0.45
                    ? THREE.MathUtils.smoothstep(p / 0.45, 0, 1)
                    : 1 - THREE.MathUtils.smoothstep((p - 0.45) / 0.55, 0, 1));
                if (this.blinkT > D) { this.blinkT = -1; this.setMorph("blink", 0); }
            }
        } else {
            this.setMorph("blink", 0);
        }

        // --- eye darting --------------------------------------------
        if (!asleep) {
            this.lookNext -= dt;
            if (this.lookNext <= 0) {
                const wander = this.state === STATES.THINKING ? 0.85 : 0.5;
                this.lookTarget.set(
                    (Math.random() * 2 - 1) * wander,
                    (Math.random() * 2 - 1) * wander * 0.6
                );
                this.lookNext = 1.4 + Math.random() * 2.4;
            }
        } else {
            this.lookTarget.set(0, 0);
        }
        this.lookNow.lerp(this.lookTarget, Math.min(1, dt * 7));
        const lx = this.lookNow.x, ly = this.lookNow.y;
        this.setMorph("look_L", Math.max(0, -lx));
        this.setMorph("look_R", Math.max(0,  lx));
        this.setMorph("look_U", Math.max(0,  ly));
        this.setMorph("look_D", Math.max(0, -ly));

        // --- mouth flap while speaking -------------------------------
        const want = this.state === STATES.TALKING
            ? 0.30 + 0.30 * (Math.sin(time * 15.5) * 0.5 + 0.5)
                   + 0.14 * (Math.sin(time * 26.3 + 1.1) * 0.5 + 0.5)
            : 0;
        this.mouth += (want - this.mouth) * Math.min(1, dt * 16);
        if (this.mouth > 0.004) this.setMorph("mouth_open", this.mouth);
    }

    /* ------------------------------------------------------------ loop */
    animate() {
        requestAnimationFrame(() => this.animate());
        const dt = Math.min(this.clock.getDelta(), 0.05);
        const time = this.clock.elapsedTime;

        if (this.mixer) this.mixer.update(dt);
        if (this.ready) {
            this.faceTick(dt, time);
            // gentle float so the character never sits perfectly still
            this.root.position.y = Math.sin(time * 1.1) * 0.012;
            this.root.rotation.y = Math.sin(time * 0.37) * 0.05;
        }

        const quiet = (performance.now() - this.lastInteractionAt) / 1000;
        if (this.state === STATES.IDLE && quiet > this.autoSleepAfter) this.sleep();

        this.renderer.render(this.scene, this.camera);
    }

    /* ---------------------------------------------------------- events */
    bindEvents() {
        window.addEventListener("resize", () => this.resize());
        this.container.addEventListener("pointerdown", (e) => this.startDrag(e));
        window.addEventListener("pointermove", (e) => this.onDrag(e));
        window.addEventListener("pointerup", () => this.endDrag());
        this.container.addEventListener("dblclick", () => {
            this.lastInteractionAt = performance.now();
            this.applyState(STATES.HAPPY, 0.15);
        });
        this.container.addEventListener("pointermove", (e) => {
            const r = this.container.getBoundingClientRect();
            this.look(((e.clientX - r.left) / r.width) * 2 - 1,
                      -(((e.clientY - r.top) / r.height) * 2 - 1));
        });
    }

    startDrag(event) {
        this.dragging = true;
        this.dragMoved = false;
        this.lastInteractionAt = performance.now();
        this.container.setPointerCapture?.(event.pointerId);
        const rect = this.container.getBoundingClientRect();
        this.pointerOffset.x = event.clientX - rect.left;
        this.pointerOffset.y = event.clientY - rect.top;
        if (this.state === STATES.SLEEPING) this.setState(STATES.IDLE);
    }

    onDrag(event) {
        if (!this.dragging) return;
        this.dragMoved = true;
        const width = this.container.offsetWidth;
        const height = this.container.offsetHeight;
        const x = Math.max(8, Math.min(window.innerWidth - width - 8, event.clientX - this.pointerOffset.x));
        const y = Math.max(8, Math.min(window.innerHeight - height - 8, event.clientY - this.pointerOffset.y));
        this.container.style.left = `${x}px`;
        this.container.style.top = `${y}px`;
        this.container.style.right = "auto";
        this.container.style.bottom = "auto";
    }

    endDrag() {
        if (!this.dragging) return;
        this.dragging = false;
        this.lastInteractionAt = performance.now();
    }

    resize() {
        const width = this.container.clientWidth || 220;
        const height = this.container.clientHeight || 260;
        this.camera.aspect = width / height;
        if (this.modelSize) {
            const fov = THREE.MathUtils.degToRad(this.camera.fov);
            const fit = Math.max(this.modelSize.y, this.modelSize.x / Math.max(this.camera.aspect, 0.01));
            this.frameDistance = (fit / 2) / Math.tan(fov / 2) * 1.18;
            this.camera.position.set(0, 0, this.frameDistance);
            this.camera.near = this.frameDistance * 0.05;
            this.camera.far = this.frameDistance * 6;
        }
        this.camera.updateProjectionMatrix();
        this.renderer.setSize(width, height, false);
    }
}

function initCherryMascot() {
    const container = document.getElementById("cherry-mascot");
    if (!container) return;
    window.CherryMascot = new CherryMascotController(container);
}

if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initCherryMascot);
} else {
    initCherryMascot();
}

export { CherryMascotController, STATES };
