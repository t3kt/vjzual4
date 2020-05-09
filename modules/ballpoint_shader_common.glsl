// created by florian berger (flockaroo) - 2018
// License Creative Commons Attribution-NonCommercial-ShareAlike 3.0 Unported License.

// ballpoint line drawing

// drawing a line segment from previous position to actual 
// for every particle (ballpoint tip)

#define PI 3.1415927

#define PNUM 200

struct Particle {
    vec2 pos;
    vec2 vel;
    int idx;
};

int particleIdx(vec2 coord, sampler2D s)
{
    ivec2 ires=textureSize(s,0);
    return int(coord.x)+int(coord.y)*ires.x;
}

vec2 particleCoord(int idx, sampler2D s)
{
    ivec2 ires=textureSize(s,0);
    return vec2(idx%ires.x,idx/ires.x)+.5;
}

vec4 getPixel(vec2 coord, sampler2D s)
{
    return texelFetch(s,ivec2(coord),0);
}

void readParticle(inout Particle p, vec2 coord, sampler2D s)
{
    vec4 pix=getPixel(coord,s);
    p.pos=pix.xy;
    p.vel=pix.zw;
    p.idx=particleIdx(coord,s);
}

void readParticle(inout Particle p, int idx, sampler2D s)
{
    readParticle(p,particleCoord(idx,s),s);
}

void writeParticle(Particle p, inout vec4 col, vec2 coord, sampler2D s)
{
    if (particleIdx(coord,s)%PNUM==p.idx) col=vec4(p.pos,p.vel);
}

vec4 getRand(vec2 pos, sampler2D s)
{
    vec2 rres=vec2(textureSize(s,0));
    return textureLod(s,pos/rres,0.);
}

vec4 getRand(int idx, sampler2D s)
{
    ivec2 rres=textureSize(s,0);
    idx=idx%(rres.x*rres.y);
    return texelFetch(s,ivec2(idx%rres.x,idx/rres.x),0);
}

void initParticle(inout Particle p, sampler2D s, sampler2D sr, int frame)
{
    vec2 res=vec2(textureSize(s,0));
    //p.pos = vec2((p.idx/2)%NUM_X,(p.idx/2)/NUM_X)*res/vec2(NUM_X,NUM_Y);
    p.pos=getRand(frame+p.idx,sr).xy*res.xy;
    p.vel = (getRand(p.pos,sr).xy-.5)*(float(p.idx%2)-.5)*300.;
}

vec4 getCol(vec2 pos, sampler2D s, vec2 res)
{
    return textureLod(s,pos/res.xy,0.);
}

float getVal(vec2 pos, sampler2D s, vec2 res)
{
    return dot(getCol(pos,s,res).xyz,vec3(1)/3.);
}

vec2 getGrad(vec2 pos, float eps, sampler2D s, vec2 res)
{
    vec2 d=vec2(eps,0);
    return vec2(
        getVal(pos+d.xy,s,res)-getVal(pos-d.xy,s,res),
        getVal(pos+d.yx,s,res)-getVal(pos-d.yx,s,res)
        )/eps/2.;
}
