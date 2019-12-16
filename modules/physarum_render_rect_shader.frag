flat in float deposit;
flat in vec4 color;
flat in vec4 state;

in Vertex
{
	vec2 texCoord0;
} iVert;

// Output variable for the color
layout(location = 0) out vec4 oFragColor;
layout(location = 1) out vec4 oStateOut;
void main()
{
	float d = 1.-length(iVert.texCoord0);
	d = clamp(d, 0., 1.);
	
	//d = pow(d, 1.5);
	vec4 outcol = vec4(deposit);
//	outcol *= d;
	outcol *= color;

	oFragColor = TDOutputSwizzle(outcol);
	oStateOut = state;
}
