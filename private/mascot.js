import * as THREE from "https://unpkg.com/three@0.160.0/build/three.module.js";

const STATES = {
    IDLE: "idle",
    THINKING: "thinking",
    TALKING: "talking",
    JUMPING: "jumping",
    SLEEPING: "sleeping",
    ERROR: "error"
};

class CherryMascotController {
    constructor(container) {
        this.container = container;
        this.state = STATES.IDLE;
        this.stateStartedAt = performance.now();
        this.lastInteractionAt = performance.now();
        this.jumpStartedAt = 0;
        this.dragging = false;
        this.pointerOffset = { x: 0, y: 0 };

        this.scene = new THREE.Scene();
        this.camera = new THREE.PerspectiveCamera(38, 1, 0.1, 100);
        this.camera.position.set(0, 0.45, 7.1);

        this.renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true });
        this.renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
        this.renderer.outputColorSpace = THREE.SRGBColorSpace;
        this.container.appendChild(this.renderer.domElement);

        this.clock = new THREE.Clock();
        this.parts = {};
        this.createLights();
        this.createCharacter();
        this.bindEvents();
        this.resize();
        this.animate();
    }

    createLights() {
        const ambient = new THREE.HemisphereLight(0xffffff, 0x4b251f, 2.4);
        this.scene.add(ambient);

        const key = new THREE.DirectionalLight(0xffffff, 3.1);
        key.position.set(-3, 4, 5);
        this.scene.add(key);

        const rim = new THREE.DirectionalLight(0xffc2cf, 1.2);
        rim.position.set(4, 2, 3);
        this.scene.add(rim);
    }

    material(color, roughness = 0.58, metalness = 0.02) {
        return new THREE.MeshStandardMaterial({
            color,
            roughness,
            metalness
        });
    }

    createCharacter() {
        const root = new THREE.Group();
        this.scene.add(root);
        this.parts.root = root;

        const red = this.material(0xf1293b, 0.48);
        const darkRed = this.material(0x8f1323, 0.62);
        const green = this.material(0x78b949, 0.55);
        const darkGreen = this.material(0x285d31, 0.62);
        const white = this.material(0xffffff, 0.32);
        const brown = this.material(0x651d1d, 0.45);
        const blush = this.material(0xff7b83, 0.64);

        const body = new THREE.Mesh(new THREE.SphereGeometry(1.55, 64, 48), red);
        body.scale.set(1.06, 1.0, 0.92);
        body.castShadow = true;
        root.add(body);
        this.parts.body = body;

        const shade = new THREE.Mesh(new THREE.SphereGeometry(1.57, 48, 32), darkRed);
        shade.scale.set(1.04, 0.98, 0.9);
        shade.position.set(0.22, -0.04, -0.05);
        shade.rotation.y = -0.32;
        shade.material.transparent = true;
        shade.material.opacity = 0.22;
        root.add(shade);

        const highlight = new THREE.Mesh(new THREE.SphereGeometry(0.32, 24, 18), this.material(0xff8f93, 0.28));
        highlight.scale.set(1.0, 0.48, 0.18);
        highlight.position.set(-0.78, 0.62, 1.12);
        highlight.rotation.z = 0.7;
        root.add(highlight);

        const stem = new THREE.Mesh(new THREE.CylinderGeometry(0.14, 0.19, 2.25, 24), green);
        stem.position.set(0.4, 1.52, 0);
        stem.rotation.z = -0.42;
        root.add(stem);
        this.parts.stem = stem;

        const stemTip = new THREE.Mesh(new THREE.SphereGeometry(0.22, 24, 16), green);
        stemTip.scale.set(1.2, 0.78, 0.78);
        stemTip.position.set(0.92, 2.53, 0);
        stemTip.rotation.z = -0.42;
        root.add(stemTip);

        const leafLeft = this.createLeaf(green, darkGreen);
        leafLeft.position.set(-0.42, 2.03, 0.02);
        leafLeft.rotation.set(0.08, 0.18, -0.38);
        leafLeft.scale.set(0.82, 0.42, 0.18);
        root.add(leafLeft);
        this.parts.leafLeft = leafLeft;

        const leafRight = this.createLeaf(green, darkGreen);
        leafRight.position.set(0.95, 1.72, 0.02);
        leafRight.rotation.set(0.08, -0.28, 1.02);
        leafRight.scale.set(0.88, 0.46, 0.18);
        root.add(leafRight);
        this.parts.leafRight = leafRight;

        this.parts.leftArm = this.createLimb(root, green, -1.23, 0.05, 0.78, 1);
        this.parts.rightArm = this.createLimb(root, green, 1.26, -0.2, -0.6, -1);
        this.parts.leftLeg = this.createLeg(root, green, -0.55);
        this.parts.rightLeg = this.createLeg(root, green, 0.55);

        this.createFace(root, white, brown, blush);
    }

    createLeaf(green, darkGreen) {
        const group = new THREE.Group();
        const leaf = new THREE.Mesh(new THREE.SphereGeometry(1, 32, 16), green);
        leaf.scale.set(0.95, 0.38, 0.08);
        group.add(leaf);

        const vein = new THREE.Mesh(new THREE.CylinderGeometry(0.018, 0.018, 1.55, 12), darkGreen);
        vein.rotation.z = Math.PI / 2;
        vein.scale.y = 0.85;
        vein.position.z = 0.08;
        group.add(vein);
        return group;
    }

    createLimb(root, material, x, y, angle, side) {
        const group = new THREE.Group();
        group.position.set(x, y, 0.2);
        group.rotation.z = angle;

        const upper = new THREE.Mesh(new THREE.CylinderGeometry(0.08, 0.1, 0.9, 18), material);
        upper.position.y = -0.43;
        group.add(upper);

        const hand = new THREE.Mesh(new THREE.SphereGeometry(0.22, 24, 16), material);
        hand.scale.set(1.0, 0.82, 0.55);
        hand.position.set(0, -0.92, 0.03);
        group.add(hand);

        for (let i = 0; i < 4; i += 1) {
            const finger = new THREE.Mesh(new THREE.SphereGeometry(0.07, 12, 8), material);
            finger.position.set((i - 1.5) * 0.08 * side, -1.1, 0.04);
            finger.scale.set(0.7, 1.1, 0.55);
            group.add(finger);
        }

        root.add(group);
        return group;
    }

    createLeg(root, material, x) {
        const group = new THREE.Group();
        group.position.set(x, -1.3, 0);

        const leg = new THREE.Mesh(new THREE.CylinderGeometry(0.08, 0.1, 0.95, 18), material);
        leg.position.y = -0.38;
        group.add(leg);

        const foot = new THREE.Mesh(new THREE.SphereGeometry(0.26, 24, 16), material);
        foot.scale.set(1.35, 0.48, 0.75);
        foot.position.set(0.05 * Math.sign(x || 1), -0.92, 0.13);
        group.add(foot);

        root.add(group);
        return group;
    }

    createFace(root, white, brown, blush) {
        const leftEye = this.createEye(white, brown);
        leftEye.position.set(-0.48, 0.3, 1.23);
        root.add(leftEye);
        this.parts.leftEye = leftEye;

        const rightEye = this.createEye(white, brown);
        rightEye.position.set(0.48, 0.31, 1.23);
        root.add(rightEye);
        this.parts.rightEye = rightEye;

        const mouth = new THREE.Mesh(new THREE.TorusGeometry(0.34, 0.025, 10, 48, Math.PI), brown);
        mouth.position.set(0.02, -0.35, 1.33);
        mouth.rotation.set(0, 0, Math.PI);
        mouth.scale.set(1.05, 0.5, 1);
        root.add(mouth);
        this.parts.mouth = mouth;

        const mouthTalk = new THREE.Mesh(new THREE.SphereGeometry(0.16, 24, 16), brown);
        mouthTalk.position.set(0.03, -0.38, 1.34);
        mouthTalk.scale.set(1, 0.42, 0.18);
        mouthTalk.visible = false;
        root.add(mouthTalk);
        this.parts.mouthTalk = mouthTalk;

        const leftBlush = new THREE.Mesh(new THREE.SphereGeometry(0.2, 24, 12), blush);
        leftBlush.position.set(-0.72, -0.16, 1.21);
        leftBlush.scale.set(1.35, 0.48, 0.12);
        root.add(leftBlush);

        const rightBlush = leftBlush.clone();
        rightBlush.position.x = 0.72;
        root.add(rightBlush);

        const browMaterial = brown;
        const leftBrow = new THREE.Mesh(new THREE.CylinderGeometry(0.018, 0.018, 0.28, 8), browMaterial);
        leftBrow.position.set(-0.52, 0.76, 1.25);
        leftBrow.rotation.z = -1.22;
        root.add(leftBrow);
        this.parts.leftBrow = leftBrow;

        const rightBrow = leftBrow.clone();
        rightBrow.position.x = 0.52;
        rightBrow.rotation.z = 1.22;
        root.add(rightBrow);
        this.parts.rightBrow = rightBrow;
    }

    createEye(white, brown) {
        const group = new THREE.Group();
        const eye = new THREE.Mesh(new THREE.SphereGeometry(0.26, 32, 24), white);
        eye.scale.set(1.0, 1.12, 0.28);
        group.add(eye);

        const pupil = new THREE.Mesh(new THREE.SphereGeometry(0.11, 24, 16), brown);
        pupil.position.set(0.03, -0.02, 0.22);
        pupil.scale.set(1.0, 1.0, 0.18);
        group.add(pupil);

        const sparkle = new THREE.Mesh(new THREE.SphereGeometry(0.04, 12, 8), this.material(0xffffff, 0.2));
        sparkle.position.set(-0.04, 0.07, 0.28);
        sparkle.scale.z = 0.14;
        group.add(sparkle);

        return group;
    }

    bindEvents() {
        window.addEventListener("resize", () => this.resize());
        this.container.addEventListener("pointerdown", (event) => this.startDrag(event));
        window.addEventListener("pointermove", (event) => this.onDrag(event));
        window.addEventListener("pointerup", () => this.endDrag());
        this.container.addEventListener("dblclick", () => this.setState(STATES.JUMPING));
    }

    startDrag(event) {
        this.dragging = true;
        this.lastInteractionAt = performance.now();
        this.container.setPointerCapture?.(event.pointerId);
        const rect = this.container.getBoundingClientRect();
        this.pointerOffset.x = event.clientX - rect.left;
        this.pointerOffset.y = event.clientY - rect.top;
        this.setState(STATES.THINKING);
    }

    onDrag(event) {
        if (!this.dragging) return;
        const width = this.container.offsetWidth;
        const height = this.container.offsetHeight;
        const x = Math.max(12, Math.min(window.innerWidth - width - 12, event.clientX - this.pointerOffset.x));
        const y = Math.max(12, Math.min(window.innerHeight - height - 12, event.clientY - this.pointerOffset.y));
        this.container.style.left = `${x}px`;
        this.container.style.top = `${y}px`;
        this.container.style.right = "auto";
        this.container.style.bottom = "auto";
    }

    endDrag() {
        if (!this.dragging) return;
        this.dragging = false;
        this.setState(STATES.IDLE);
    }

    resize() {
        const width = this.container.clientWidth || 220;
        const height = this.container.clientHeight || 260;
        this.camera.aspect = width / height;
        this.camera.updateProjectionMatrix();
        this.renderer.setSize(width, height, false);
    }

    setState(nextState) {
        if (!Object.values(STATES).includes(nextState)) return;
        this.state = nextState;
        this.stateStartedAt = performance.now();
        this.lastInteractionAt = performance.now();
        if (nextState === STATES.JUMPING) {
            this.jumpStartedAt = performance.now();
        }
        if (nextState !== STATES.SLEEPING) {
            this.container.classList.remove("is-sleeping");
        }
    }

    idle() {
        this.setState(STATES.IDLE);
    }

    thinking() {
        this.setState(STATES.THINKING);
    }

    talking() {
        this.setState(STATES.TALKING);
    }

    error() {
        this.setState(STATES.ERROR);
    }

    jump() {
        this.setState(STATES.JUMPING);
    }

    sleep() {
        this.setState(STATES.SLEEPING);
    }

    animate() {
        requestAnimationFrame(() => this.animate());
        const elapsed = this.clock.getElapsedTime();
        const stateAge = (performance.now() - this.stateStartedAt) / 1000;
        const idleAge = (performance.now() - this.lastInteractionAt) / 1000;

        if (this.state === STATES.IDLE && idleAge > 35) {
            this.state = STATES.SLEEPING;
            this.stateStartedAt = performance.now();
        }

        this.applyPose(elapsed, stateAge);
        this.renderer.render(this.scene, this.camera);
    }

    applyPose(time, stateAge) {
        const root = this.parts.root;
        const body = this.parts.body;
        const bob = Math.sin(time * 2.4) * 0.05;
        root.position.set(0, bob, 0);
        root.rotation.y = Math.sin(time * 0.7) * 0.08;
        body.scale.set(1.06, 1.0 + Math.sin(time * 2.2) * 0.018, 0.92);

        this.parts.mouth.visible = true;
        this.parts.mouthTalk.visible = false;
        this.parts.leftEye.scale.set(1, 1, 1);
        this.parts.rightEye.scale.set(1, 1, 1);
        this.container.classList.remove("is-sleeping");

        const armWave = Math.sin(time * 4.5) * 0.25;
        this.parts.leftArm.rotation.z = 0.78 + armWave * 0.35;
        this.parts.rightArm.rotation.z = -0.6 - armWave * 0.18;
        this.parts.leftLeg.rotation.z = Math.sin(time * 2.5) * 0.08;
        this.parts.rightLeg.rotation.z = -Math.sin(time * 2.5) * 0.08;
        this.parts.stem.rotation.z = -0.42 + Math.sin(time * 1.8) * 0.04;
        this.parts.leafLeft.rotation.z = -0.38 + Math.sin(time * 2.2) * 0.06;
        this.parts.leafRight.rotation.z = 1.02 - Math.sin(time * 2.0) * 0.05;

        if (this.state === STATES.THINKING) {
            root.rotation.y = Math.sin(time * 2.4) * 0.18;
            this.parts.leftArm.rotation.z = 0.95 + Math.sin(time * 7) * 0.16;
            this.parts.rightArm.rotation.z = -0.2 + Math.sin(time * 4.2) * 0.1;
        }

        if (this.state === STATES.TALKING) {
            const mouthOpen = 0.5 + Math.sin(time * 14) * 0.5;
            this.parts.mouth.visible = mouthOpen < 0.45;
            this.parts.mouthTalk.visible = mouthOpen >= 0.45;
            this.parts.mouthTalk.scale.y = 0.22 + mouthOpen * 0.54;
            this.parts.leftArm.rotation.z = 1.05 + Math.sin(time * 8) * 0.22;
            this.parts.rightArm.rotation.z = -0.78 + Math.sin(time * 6) * 0.16;
        }

        if (this.state === STATES.JUMPING) {
            const t = Math.min(stateAge / 0.9, 1);
            const jump = Math.sin(t * Math.PI) * 0.9;
            root.position.y += jump;
            body.scale.set(1.06 + jump * 0.05, 1.0 - jump * 0.08, 0.92 + jump * 0.03);
            this.parts.leftArm.rotation.z = 1.55;
            this.parts.rightArm.rotation.z = -1.55;
            if (t >= 1) this.idle();
        }

        if (this.state === STATES.SLEEPING) {
            this.container.classList.add("is-sleeping");
            root.rotation.z = -0.2;
            root.position.y = -0.1 + Math.sin(time * 1.2) * 0.025;
            this.parts.leftEye.scale.y = 0.12;
            this.parts.rightEye.scale.y = 0.12;
            this.parts.leftArm.rotation.z = 0.2;
            this.parts.rightArm.rotation.z = -0.2;
        }

        if (this.state === STATES.ERROR) {
            root.rotation.z = Math.sin(time * 13) * 0.025;
            this.parts.leftBrow.rotation.z = -0.72;
            this.parts.rightBrow.rotation.z = 0.72;
            if (stateAge > 3) this.idle();
        } else {
            this.parts.leftBrow.rotation.z = -1.22;
            this.parts.rightBrow.rotation.z = 1.22;
        }
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
