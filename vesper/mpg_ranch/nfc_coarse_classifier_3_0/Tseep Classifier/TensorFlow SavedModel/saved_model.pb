��
��
:
Add
x"T
y"T
z"T"
Ttype:
2	
x
Assign
ref"T�

value"T

output_ref"T�"	
Ttype"
validate_shapebool("
use_lockingbool(�
B
AssignVariableOp
resource
value"dtype"
dtypetype�
~
BiasAdd

value"T	
bias"T
output"T" 
Ttype:
2	"-
data_formatstringNHWC:
NHWCNCHW
8
Const
output"dtype"
valuetensor"
dtypetype
�
Conv2D

input"T
filter"T
output"T"
Ttype:
2"
strides	list(int)"
use_cudnn_on_gpubool(""
paddingstring:
SAMEVALID"-
data_formatstringNHWC:
NHWCNCHW" 
	dilations	list(int)

�
FusedBatchNorm
x"T

scale"T
offset"T	
mean"T
variance"T
y"T

batch_mean"T
batch_variance"T
reserve_space_1"T
reserve_space_2"T"
Ttype:
2"
epsilonfloat%��8"-
data_formatstringNHWC:
NHWCNCHW"
is_trainingbool(
.
Identity

input"T
output"T"	
Ttype
p
MatMul
a"T
b"T
product"T"
transpose_abool( "
transpose_bbool( "
Ttype:
	2
�
MaxPool

input"T
output"T"
Ttype0:
2	"
ksize	list(int)(0"
strides	list(int)(0""
paddingstring:
SAMEVALID":
data_formatstringNHWC:
NHWCNCHWNCHW_VECT_C
e
MergeV2Checkpoints
checkpoint_prefixes
destination_prefix"
delete_old_dirsbool(�
=
Mul
x"T
y"T
z"T"
Ttype:
2	�

NoOp
M
Pack
values"T*N
output"T"
Nint(0"	
Ttype"
axisint 
C
Placeholder
output"dtype"
dtypetype"
shapeshape:
~
RandomUniform

shape"T
output"dtype"
seedint "
seed2int "
dtypetype:
2"
Ttype:
2	�
@
ReadVariableOp
resource
value"dtype"
dtypetype�
E
Relu
features"T
activations"T"
Ttype:
2	
[
Reshape
tensor"T
shape"Tshape
output"T"	
Ttype"
Tshapetype0:
2	
o
	RestoreV2

prefix
tensor_names
shape_and_slices
tensors2dtypes"
dtypes
list(type)(0�
.
Rsqrt
x"T
y"T"
Ttype:

2
l
SaveV2

prefix
tensor_names
shape_and_slices
tensors2dtypes"
dtypes
list(type)(0�
P
Shape

input"T
output"out_type"	
Ttype"
out_typetype0:
2	
H
ShardedFilename
basename	
shard

num_shards
filename
0
Sigmoid
x"T
y"T"
Ttype:

2
�
StridedSlice

input"T
begin"Index
end"Index
strides"Index
output"T"	
Ttype"
Indextype:
2	"

begin_maskint "
end_maskint "
ellipsis_maskint "
new_axis_maskint "
shrink_axis_maskint 
N

StringJoin
inputs*N

output"
Nint(0"
	separatorstring 
:
Sub
x"T
y"T
z"T"
Ttype:
2	
q
VarHandleOp
resource"
	containerstring "
shared_namestring "
dtypetype"
shapeshape�
9
VarIsInitializedOp
resource
is_initialized
�
s

VariableV2
ref"dtype�"
shapeshape"
dtypetype"
	containerstring "
shared_namestring �"serve*1.12.02v1.12.0-rc2-3-ga6d8ffae098�

global_step/Initializer/zerosConst*
value	B	 R *
_class
loc:@global_step*
dtype0	*
_output_shapes
: 
k
global_step
VariableV2*
_class
loc:@global_step*
shape: *
dtype0	*
_output_shapes
: 
�
global_step/AssignAssignglobal_stepglobal_step/Initializer/zeros*
T0	*
_class
loc:@global_step*
_output_shapes
: 
j
global_step/readIdentityglobal_step*
T0	*
_class
loc:@global_step*
_output_shapes
: 
~
PlaceholderPlaceholder*/
_output_shapes
:���������K!*$
shape:���������K!*
dtype0
�
0Conv2D_0/kernel/Initializer/random_uniform/shapeConst*%
valueB"            *"
_class
loc:@Conv2D_0/kernel*
dtype0*
_output_shapes
:
�
.Conv2D_0/kernel/Initializer/random_uniform/minConst*
valueB
 *?�J�*"
_class
loc:@Conv2D_0/kernel*
dtype0*
_output_shapes
: 
�
.Conv2D_0/kernel/Initializer/random_uniform/maxConst*
_output_shapes
: *
valueB
 *?�J>*"
_class
loc:@Conv2D_0/kernel*
dtype0
�
8Conv2D_0/kernel/Initializer/random_uniform/RandomUniformRandomUniform0Conv2D_0/kernel/Initializer/random_uniform/shape*
dtype0*&
_output_shapes
:*
T0*"
_class
loc:@Conv2D_0/kernel
�
.Conv2D_0/kernel/Initializer/random_uniform/subSub.Conv2D_0/kernel/Initializer/random_uniform/max.Conv2D_0/kernel/Initializer/random_uniform/min*
T0*"
_class
loc:@Conv2D_0/kernel*
_output_shapes
: 
�
.Conv2D_0/kernel/Initializer/random_uniform/mulMul8Conv2D_0/kernel/Initializer/random_uniform/RandomUniform.Conv2D_0/kernel/Initializer/random_uniform/sub*
T0*"
_class
loc:@Conv2D_0/kernel*&
_output_shapes
:
�
*Conv2D_0/kernel/Initializer/random_uniformAdd.Conv2D_0/kernel/Initializer/random_uniform/mul.Conv2D_0/kernel/Initializer/random_uniform/min*&
_output_shapes
:*
T0*"
_class
loc:@Conv2D_0/kernel
�
Conv2D_0/kernelVarHandleOp*
shape:*
dtype0*
_output_shapes
: * 
shared_nameConv2D_0/kernel*"
_class
loc:@Conv2D_0/kernel
o
0Conv2D_0/kernel/IsInitialized/VarIsInitializedOpVarIsInitializedOpConv2D_0/kernel*
_output_shapes
: 
�
Conv2D_0/kernel/AssignAssignVariableOpConv2D_0/kernel*Conv2D_0/kernel/Initializer/random_uniform*"
_class
loc:@Conv2D_0/kernel*
dtype0
�
#Conv2D_0/kernel/Read/ReadVariableOpReadVariableOpConv2D_0/kernel*"
_class
loc:@Conv2D_0/kernel*
dtype0*&
_output_shapes
:
�
Conv2D_0/bias/Initializer/zerosConst*
_output_shapes
:*
valueB*    * 
_class
loc:@Conv2D_0/bias*
dtype0
�
Conv2D_0/biasVarHandleOp*
shape:*
dtype0*
_output_shapes
: *
shared_nameConv2D_0/bias* 
_class
loc:@Conv2D_0/bias
k
.Conv2D_0/bias/IsInitialized/VarIsInitializedOpVarIsInitializedOpConv2D_0/bias*
_output_shapes
: 
�
Conv2D_0/bias/AssignAssignVariableOpConv2D_0/biasConv2D_0/bias/Initializer/zeros* 
_class
loc:@Conv2D_0/bias*
dtype0
�
!Conv2D_0/bias/Read/ReadVariableOpReadVariableOpConv2D_0/bias* 
_class
loc:@Conv2D_0/bias*
dtype0*
_output_shapes
:
g
Conv2D_0/dilation_rateConst*
valueB"      *
dtype0*
_output_shapes
:
v
Conv2D_0/Conv2D/ReadVariableOpReadVariableOpConv2D_0/kernel*
dtype0*&
_output_shapes
:
�
Conv2D_0/Conv2DConv2DPlaceholderConv2D_0/Conv2D/ReadVariableOp*
strides
*
paddingVALID*/
_output_shapes
:���������I*
T0
i
Conv2D_0/BiasAdd/ReadVariableOpReadVariableOpConv2D_0/bias*
dtype0*
_output_shapes
:
�
Conv2D_0/BiasAddBiasAddConv2D_0/Conv2DConv2D_0/BiasAdd/ReadVariableOp*
T0*/
_output_shapes
:���������I
a
Conv2D_0/ReluReluConv2D_0/BiasAdd*/
_output_shapes
:���������I*
T0
�
*batch_normalization/gamma/Initializer/onesConst*
valueB*  �?*,
_class"
 loc:@batch_normalization/gamma*
dtype0*
_output_shapes
:
�
batch_normalization/gammaVarHandleOp*,
_class"
 loc:@batch_normalization/gamma*
shape:*
dtype0*
_output_shapes
: **
shared_namebatch_normalization/gamma
�
:batch_normalization/gamma/IsInitialized/VarIsInitializedOpVarIsInitializedOpbatch_normalization/gamma*
_output_shapes
: 
�
 batch_normalization/gamma/AssignAssignVariableOpbatch_normalization/gamma*batch_normalization/gamma/Initializer/ones*,
_class"
 loc:@batch_normalization/gamma*
dtype0
�
-batch_normalization/gamma/Read/ReadVariableOpReadVariableOpbatch_normalization/gamma*,
_class"
 loc:@batch_normalization/gamma*
dtype0*
_output_shapes
:
�
*batch_normalization/beta/Initializer/zerosConst*
valueB*    *+
_class!
loc:@batch_normalization/beta*
dtype0*
_output_shapes
:
�
batch_normalization/betaVarHandleOp*
_output_shapes
: *)
shared_namebatch_normalization/beta*+
_class!
loc:@batch_normalization/beta*
shape:*
dtype0
�
9batch_normalization/beta/IsInitialized/VarIsInitializedOpVarIsInitializedOpbatch_normalization/beta*
_output_shapes
: 
�
batch_normalization/beta/AssignAssignVariableOpbatch_normalization/beta*batch_normalization/beta/Initializer/zeros*+
_class!
loc:@batch_normalization/beta*
dtype0
�
,batch_normalization/beta/Read/ReadVariableOpReadVariableOpbatch_normalization/beta*+
_class!
loc:@batch_normalization/beta*
dtype0*
_output_shapes
:
�
1batch_normalization/moving_mean/Initializer/zerosConst*
_output_shapes
:*
valueB*    *2
_class(
&$loc:@batch_normalization/moving_mean*
dtype0
�
batch_normalization/moving_meanVarHandleOp*
shape:*
dtype0*
_output_shapes
: *0
shared_name!batch_normalization/moving_mean*2
_class(
&$loc:@batch_normalization/moving_mean
�
@batch_normalization/moving_mean/IsInitialized/VarIsInitializedOpVarIsInitializedOpbatch_normalization/moving_mean*
_output_shapes
: 
�
&batch_normalization/moving_mean/AssignAssignVariableOpbatch_normalization/moving_mean1batch_normalization/moving_mean/Initializer/zeros*2
_class(
&$loc:@batch_normalization/moving_mean*
dtype0
�
3batch_normalization/moving_mean/Read/ReadVariableOpReadVariableOpbatch_normalization/moving_mean*2
_class(
&$loc:@batch_normalization/moving_mean*
dtype0*
_output_shapes
:
�
4batch_normalization/moving_variance/Initializer/onesConst*
valueB*  �?*6
_class,
*(loc:@batch_normalization/moving_variance*
dtype0*
_output_shapes
:
�
#batch_normalization/moving_varianceVarHandleOp*
_output_shapes
: *4
shared_name%#batch_normalization/moving_variance*6
_class,
*(loc:@batch_normalization/moving_variance*
shape:*
dtype0
�
Dbatch_normalization/moving_variance/IsInitialized/VarIsInitializedOpVarIsInitializedOp#batch_normalization/moving_variance*
_output_shapes
: 
�
*batch_normalization/moving_variance/AssignAssignVariableOp#batch_normalization/moving_variance4batch_normalization/moving_variance/Initializer/ones*6
_class,
*(loc:@batch_normalization/moving_variance*
dtype0
�
7batch_normalization/moving_variance/Read/ReadVariableOpReadVariableOp#batch_normalization/moving_variance*6
_class,
*(loc:@batch_normalization/moving_variance*
dtype0*
_output_shapes
:
x
"batch_normalization/ReadVariableOpReadVariableOpbatch_normalization/gamma*
dtype0*
_output_shapes
:
y
$batch_normalization/ReadVariableOp_1ReadVariableOpbatch_normalization/beta*
dtype0*
_output_shapes
:
�
1batch_normalization/FusedBatchNorm/ReadVariableOpReadVariableOpbatch_normalization/moving_mean*
dtype0*
_output_shapes
:
�
3batch_normalization/FusedBatchNorm/ReadVariableOp_1ReadVariableOp#batch_normalization/moving_variance*
_output_shapes
:*
dtype0
�
"batch_normalization/FusedBatchNormFusedBatchNormConv2D_0/Relu"batch_normalization/ReadVariableOp$batch_normalization/ReadVariableOp_11batch_normalization/FusedBatchNorm/ReadVariableOp3batch_normalization/FusedBatchNorm/ReadVariableOp_1*
T0*
is_training( *G
_output_shapes5
3:���������I::::*
epsilon%o�:
^
batch_normalization/ConstConst*
valueB
 *�p}?*
dtype0*
_output_shapes
: 
�
max_pooling2d/MaxPoolMaxPool"batch_normalization/FusedBatchNorm*
strides
*
ksize
*
paddingVALID*/
_output_shapes
:���������$
�
0Conv2D_1/kernel/Initializer/random_uniform/shapeConst*
_output_shapes
:*%
valueB"             *"
_class
loc:@Conv2D_1/kernel*
dtype0
�
.Conv2D_1/kernel/Initializer/random_uniform/minConst*
valueB
 *�[�*"
_class
loc:@Conv2D_1/kernel*
dtype0*
_output_shapes
: 
�
.Conv2D_1/kernel/Initializer/random_uniform/maxConst*
_output_shapes
: *
valueB
 *�[�=*"
_class
loc:@Conv2D_1/kernel*
dtype0
�
8Conv2D_1/kernel/Initializer/random_uniform/RandomUniformRandomUniform0Conv2D_1/kernel/Initializer/random_uniform/shape*&
_output_shapes
: *
T0*"
_class
loc:@Conv2D_1/kernel*
dtype0
�
.Conv2D_1/kernel/Initializer/random_uniform/subSub.Conv2D_1/kernel/Initializer/random_uniform/max.Conv2D_1/kernel/Initializer/random_uniform/min*
_output_shapes
: *
T0*"
_class
loc:@Conv2D_1/kernel
�
.Conv2D_1/kernel/Initializer/random_uniform/mulMul8Conv2D_1/kernel/Initializer/random_uniform/RandomUniform.Conv2D_1/kernel/Initializer/random_uniform/sub*
T0*"
_class
loc:@Conv2D_1/kernel*&
_output_shapes
: 
�
*Conv2D_1/kernel/Initializer/random_uniformAdd.Conv2D_1/kernel/Initializer/random_uniform/mul.Conv2D_1/kernel/Initializer/random_uniform/min*
T0*"
_class
loc:@Conv2D_1/kernel*&
_output_shapes
: 
�
Conv2D_1/kernelVarHandleOp* 
shared_nameConv2D_1/kernel*"
_class
loc:@Conv2D_1/kernel*
shape: *
dtype0*
_output_shapes
: 
o
0Conv2D_1/kernel/IsInitialized/VarIsInitializedOpVarIsInitializedOpConv2D_1/kernel*
_output_shapes
: 
�
Conv2D_1/kernel/AssignAssignVariableOpConv2D_1/kernel*Conv2D_1/kernel/Initializer/random_uniform*"
_class
loc:@Conv2D_1/kernel*
dtype0
�
#Conv2D_1/kernel/Read/ReadVariableOpReadVariableOpConv2D_1/kernel*"
_class
loc:@Conv2D_1/kernel*
dtype0*&
_output_shapes
: 
�
Conv2D_1/bias/Initializer/zerosConst*
_output_shapes
: *
valueB *    * 
_class
loc:@Conv2D_1/bias*
dtype0
�
Conv2D_1/biasVarHandleOp* 
_class
loc:@Conv2D_1/bias*
shape: *
dtype0*
_output_shapes
: *
shared_nameConv2D_1/bias
k
.Conv2D_1/bias/IsInitialized/VarIsInitializedOpVarIsInitializedOpConv2D_1/bias*
_output_shapes
: 
�
Conv2D_1/bias/AssignAssignVariableOpConv2D_1/biasConv2D_1/bias/Initializer/zeros* 
_class
loc:@Conv2D_1/bias*
dtype0
�
!Conv2D_1/bias/Read/ReadVariableOpReadVariableOpConv2D_1/bias*
_output_shapes
: * 
_class
loc:@Conv2D_1/bias*
dtype0
g
Conv2D_1/dilation_rateConst*
valueB"      *
dtype0*
_output_shapes
:
v
Conv2D_1/Conv2D/ReadVariableOpReadVariableOpConv2D_1/kernel*
dtype0*&
_output_shapes
: 
�
Conv2D_1/Conv2DConv2Dmax_pooling2d/MaxPoolConv2D_1/Conv2D/ReadVariableOp*
strides
*
paddingVALID*/
_output_shapes
:���������" *
T0
i
Conv2D_1/BiasAdd/ReadVariableOpReadVariableOpConv2D_1/bias*
dtype0*
_output_shapes
: 
�
Conv2D_1/BiasAddBiasAddConv2D_1/Conv2DConv2D_1/BiasAdd/ReadVariableOp*
T0*/
_output_shapes
:���������" 
a
Conv2D_1/ReluReluConv2D_1/BiasAdd*
T0*/
_output_shapes
:���������" 
�
,batch_normalization_1/gamma/Initializer/onesConst*
valueB *  �?*.
_class$
" loc:@batch_normalization_1/gamma*
dtype0*
_output_shapes
: 
�
batch_normalization_1/gammaVarHandleOp*,
shared_namebatch_normalization_1/gamma*.
_class$
" loc:@batch_normalization_1/gamma*
shape: *
dtype0*
_output_shapes
: 
�
<batch_normalization_1/gamma/IsInitialized/VarIsInitializedOpVarIsInitializedOpbatch_normalization_1/gamma*
_output_shapes
: 
�
"batch_normalization_1/gamma/AssignAssignVariableOpbatch_normalization_1/gamma,batch_normalization_1/gamma/Initializer/ones*.
_class$
" loc:@batch_normalization_1/gamma*
dtype0
�
/batch_normalization_1/gamma/Read/ReadVariableOpReadVariableOpbatch_normalization_1/gamma*.
_class$
" loc:@batch_normalization_1/gamma*
dtype0*
_output_shapes
: 
�
,batch_normalization_1/beta/Initializer/zerosConst*
valueB *    *-
_class#
!loc:@batch_normalization_1/beta*
dtype0*
_output_shapes
: 
�
batch_normalization_1/betaVarHandleOp*
_output_shapes
: *+
shared_namebatch_normalization_1/beta*-
_class#
!loc:@batch_normalization_1/beta*
shape: *
dtype0
�
;batch_normalization_1/beta/IsInitialized/VarIsInitializedOpVarIsInitializedOpbatch_normalization_1/beta*
_output_shapes
: 
�
!batch_normalization_1/beta/AssignAssignVariableOpbatch_normalization_1/beta,batch_normalization_1/beta/Initializer/zeros*-
_class#
!loc:@batch_normalization_1/beta*
dtype0
�
.batch_normalization_1/beta/Read/ReadVariableOpReadVariableOpbatch_normalization_1/beta*-
_class#
!loc:@batch_normalization_1/beta*
dtype0*
_output_shapes
: 
�
3batch_normalization_1/moving_mean/Initializer/zerosConst*
valueB *    *4
_class*
(&loc:@batch_normalization_1/moving_mean*
dtype0*
_output_shapes
: 
�
!batch_normalization_1/moving_meanVarHandleOp*
dtype0*
_output_shapes
: *2
shared_name#!batch_normalization_1/moving_mean*4
_class*
(&loc:@batch_normalization_1/moving_mean*
shape: 
�
Bbatch_normalization_1/moving_mean/IsInitialized/VarIsInitializedOpVarIsInitializedOp!batch_normalization_1/moving_mean*
_output_shapes
: 
�
(batch_normalization_1/moving_mean/AssignAssignVariableOp!batch_normalization_1/moving_mean3batch_normalization_1/moving_mean/Initializer/zeros*4
_class*
(&loc:@batch_normalization_1/moving_mean*
dtype0
�
5batch_normalization_1/moving_mean/Read/ReadVariableOpReadVariableOp!batch_normalization_1/moving_mean*4
_class*
(&loc:@batch_normalization_1/moving_mean*
dtype0*
_output_shapes
: 
�
6batch_normalization_1/moving_variance/Initializer/onesConst*
_output_shapes
: *
valueB *  �?*8
_class.
,*loc:@batch_normalization_1/moving_variance*
dtype0
�
%batch_normalization_1/moving_varianceVarHandleOp*6
shared_name'%batch_normalization_1/moving_variance*8
_class.
,*loc:@batch_normalization_1/moving_variance*
shape: *
dtype0*
_output_shapes
: 
�
Fbatch_normalization_1/moving_variance/IsInitialized/VarIsInitializedOpVarIsInitializedOp%batch_normalization_1/moving_variance*
_output_shapes
: 
�
,batch_normalization_1/moving_variance/AssignAssignVariableOp%batch_normalization_1/moving_variance6batch_normalization_1/moving_variance/Initializer/ones*8
_class.
,*loc:@batch_normalization_1/moving_variance*
dtype0
�
9batch_normalization_1/moving_variance/Read/ReadVariableOpReadVariableOp%batch_normalization_1/moving_variance*8
_class.
,*loc:@batch_normalization_1/moving_variance*
dtype0*
_output_shapes
: 
|
$batch_normalization_1/ReadVariableOpReadVariableOpbatch_normalization_1/gamma*
dtype0*
_output_shapes
: 
}
&batch_normalization_1/ReadVariableOp_1ReadVariableOpbatch_normalization_1/beta*
dtype0*
_output_shapes
: 
�
3batch_normalization_1/FusedBatchNorm/ReadVariableOpReadVariableOp!batch_normalization_1/moving_mean*
dtype0*
_output_shapes
: 
�
5batch_normalization_1/FusedBatchNorm/ReadVariableOp_1ReadVariableOp%batch_normalization_1/moving_variance*
dtype0*
_output_shapes
: 
�
$batch_normalization_1/FusedBatchNormFusedBatchNormConv2D_1/Relu$batch_normalization_1/ReadVariableOp&batch_normalization_1/ReadVariableOp_13batch_normalization_1/FusedBatchNorm/ReadVariableOp5batch_normalization_1/FusedBatchNorm/ReadVariableOp_1*
is_training( *G
_output_shapes5
3:���������" : : : : *
epsilon%o�:*
T0
`
batch_normalization_1/ConstConst*
valueB
 *�p}?*
dtype0*
_output_shapes
: 
�
max_pooling2d_1/MaxPoolMaxPool$batch_normalization_1/FusedBatchNorm*
ksize
*
paddingVALID*/
_output_shapes
:��������� *
strides

T
flatten/ShapeShapemax_pooling2d_1/MaxPool*
T0*
_output_shapes
:
e
flatten/strided_slice/stackConst*
dtype0*
_output_shapes
:*
valueB: 
g
flatten/strided_slice/stack_1Const*
valueB:*
dtype0*
_output_shapes
:
g
flatten/strided_slice/stack_2Const*
valueB:*
dtype0*
_output_shapes
:
�
flatten/strided_sliceStridedSliceflatten/Shapeflatten/strided_slice/stackflatten/strided_slice/stack_1flatten/strided_slice/stack_2*
T0*
Index0*
shrink_axis_mask*
_output_shapes
: 
b
flatten/Reshape/shape/1Const*
valueB :
���������*
dtype0*
_output_shapes
: 
{
flatten/Reshape/shapePackflatten/strided_sliceflatten/Reshape/shape/1*
T0*
N*
_output_shapes
:
}
flatten/ReshapeReshapemax_pooling2d_1/MaxPoolflatten/Reshape/shape*
T0*(
_output_shapes
:����������
�
/Dense_0/kernel/Initializer/random_uniform/shapeConst*
dtype0*
_output_shapes
:*
valueB"�     *!
_class
loc:@Dense_0/kernel
�
-Dense_0/kernel/Initializer/random_uniform/minConst*
valueB
 *�//�*!
_class
loc:@Dense_0/kernel*
dtype0*
_output_shapes
: 
�
-Dense_0/kernel/Initializer/random_uniform/maxConst*
valueB
 *�//=*!
_class
loc:@Dense_0/kernel*
dtype0*
_output_shapes
: 
�
7Dense_0/kernel/Initializer/random_uniform/RandomUniformRandomUniform/Dense_0/kernel/Initializer/random_uniform/shape*
T0*!
_class
loc:@Dense_0/kernel*
dtype0*
_output_shapes
:	�
�
-Dense_0/kernel/Initializer/random_uniform/subSub-Dense_0/kernel/Initializer/random_uniform/max-Dense_0/kernel/Initializer/random_uniform/min*
T0*!
_class
loc:@Dense_0/kernel*
_output_shapes
: 
�
-Dense_0/kernel/Initializer/random_uniform/mulMul7Dense_0/kernel/Initializer/random_uniform/RandomUniform-Dense_0/kernel/Initializer/random_uniform/sub*
T0*!
_class
loc:@Dense_0/kernel*
_output_shapes
:	�
�
)Dense_0/kernel/Initializer/random_uniformAdd-Dense_0/kernel/Initializer/random_uniform/mul-Dense_0/kernel/Initializer/random_uniform/min*
T0*!
_class
loc:@Dense_0/kernel*
_output_shapes
:	�
�
Dense_0/kernelVarHandleOp*
shape:	�*
dtype0*
_output_shapes
: *
shared_nameDense_0/kernel*!
_class
loc:@Dense_0/kernel
m
/Dense_0/kernel/IsInitialized/VarIsInitializedOpVarIsInitializedOpDense_0/kernel*
_output_shapes
: 
�
Dense_0/kernel/AssignAssignVariableOpDense_0/kernel)Dense_0/kernel/Initializer/random_uniform*!
_class
loc:@Dense_0/kernel*
dtype0
�
"Dense_0/kernel/Read/ReadVariableOpReadVariableOpDense_0/kernel*
dtype0*
_output_shapes
:	�*!
_class
loc:@Dense_0/kernel
�
Dense_0/bias/Initializer/zerosConst*
valueB*    *
_class
loc:@Dense_0/bias*
dtype0*
_output_shapes
:
�
Dense_0/biasVarHandleOp*
shape:*
dtype0*
_output_shapes
: *
shared_nameDense_0/bias*
_class
loc:@Dense_0/bias
i
-Dense_0/bias/IsInitialized/VarIsInitializedOpVarIsInitializedOpDense_0/bias*
_output_shapes
: 
�
Dense_0/bias/AssignAssignVariableOpDense_0/biasDense_0/bias/Initializer/zeros*
_class
loc:@Dense_0/bias*
dtype0
�
 Dense_0/bias/Read/ReadVariableOpReadVariableOpDense_0/bias*
_class
loc:@Dense_0/bias*
dtype0*
_output_shapes
:
m
Dense_0/MatMul/ReadVariableOpReadVariableOpDense_0/kernel*
dtype0*
_output_shapes
:	�
z
Dense_0/MatMulMatMulflatten/ReshapeDense_0/MatMul/ReadVariableOp*
T0*'
_output_shapes
:���������
g
Dense_0/BiasAdd/ReadVariableOpReadVariableOpDense_0/bias*
dtype0*
_output_shapes
:
|
Dense_0/BiasAddBiasAddDense_0/MatMulDense_0/BiasAdd/ReadVariableOp*
T0*'
_output_shapes
:���������
W
Dense_0/ReluReluDense_0/BiasAdd*
T0*'
_output_shapes
:���������
�
,batch_normalization_2/gamma/Initializer/onesConst*
valueB*  �?*.
_class$
" loc:@batch_normalization_2/gamma*
dtype0*
_output_shapes
:
�
batch_normalization_2/gammaVarHandleOp*
dtype0*
_output_shapes
: *,
shared_namebatch_normalization_2/gamma*.
_class$
" loc:@batch_normalization_2/gamma*
shape:
�
<batch_normalization_2/gamma/IsInitialized/VarIsInitializedOpVarIsInitializedOpbatch_normalization_2/gamma*
_output_shapes
: 
�
"batch_normalization_2/gamma/AssignAssignVariableOpbatch_normalization_2/gamma,batch_normalization_2/gamma/Initializer/ones*.
_class$
" loc:@batch_normalization_2/gamma*
dtype0
�
/batch_normalization_2/gamma/Read/ReadVariableOpReadVariableOpbatch_normalization_2/gamma*.
_class$
" loc:@batch_normalization_2/gamma*
dtype0*
_output_shapes
:
�
,batch_normalization_2/beta/Initializer/zerosConst*
dtype0*
_output_shapes
:*
valueB*    *-
_class#
!loc:@batch_normalization_2/beta
�
batch_normalization_2/betaVarHandleOp*+
shared_namebatch_normalization_2/beta*-
_class#
!loc:@batch_normalization_2/beta*
shape:*
dtype0*
_output_shapes
: 
�
;batch_normalization_2/beta/IsInitialized/VarIsInitializedOpVarIsInitializedOpbatch_normalization_2/beta*
_output_shapes
: 
�
!batch_normalization_2/beta/AssignAssignVariableOpbatch_normalization_2/beta,batch_normalization_2/beta/Initializer/zeros*-
_class#
!loc:@batch_normalization_2/beta*
dtype0
�
.batch_normalization_2/beta/Read/ReadVariableOpReadVariableOpbatch_normalization_2/beta*-
_class#
!loc:@batch_normalization_2/beta*
dtype0*
_output_shapes
:
�
3batch_normalization_2/moving_mean/Initializer/zerosConst*
valueB*    *4
_class*
(&loc:@batch_normalization_2/moving_mean*
dtype0*
_output_shapes
:
�
!batch_normalization_2/moving_meanVarHandleOp*4
_class*
(&loc:@batch_normalization_2/moving_mean*
shape:*
dtype0*
_output_shapes
: *2
shared_name#!batch_normalization_2/moving_mean
�
Bbatch_normalization_2/moving_mean/IsInitialized/VarIsInitializedOpVarIsInitializedOp!batch_normalization_2/moving_mean*
_output_shapes
: 
�
(batch_normalization_2/moving_mean/AssignAssignVariableOp!batch_normalization_2/moving_mean3batch_normalization_2/moving_mean/Initializer/zeros*4
_class*
(&loc:@batch_normalization_2/moving_mean*
dtype0
�
5batch_normalization_2/moving_mean/Read/ReadVariableOpReadVariableOp!batch_normalization_2/moving_mean*
dtype0*
_output_shapes
:*4
_class*
(&loc:@batch_normalization_2/moving_mean
�
6batch_normalization_2/moving_variance/Initializer/onesConst*
valueB*  �?*8
_class.
,*loc:@batch_normalization_2/moving_variance*
dtype0*
_output_shapes
:
�
%batch_normalization_2/moving_varianceVarHandleOp*
dtype0*
_output_shapes
: *6
shared_name'%batch_normalization_2/moving_variance*8
_class.
,*loc:@batch_normalization_2/moving_variance*
shape:
�
Fbatch_normalization_2/moving_variance/IsInitialized/VarIsInitializedOpVarIsInitializedOp%batch_normalization_2/moving_variance*
_output_shapes
: 
�
,batch_normalization_2/moving_variance/AssignAssignVariableOp%batch_normalization_2/moving_variance6batch_normalization_2/moving_variance/Initializer/ones*
dtype0*8
_class.
,*loc:@batch_normalization_2/moving_variance
�
9batch_normalization_2/moving_variance/Read/ReadVariableOpReadVariableOp%batch_normalization_2/moving_variance*
dtype0*
_output_shapes
:*8
_class.
,*loc:@batch_normalization_2/moving_variance
�
.batch_normalization_2/batchnorm/ReadVariableOpReadVariableOp%batch_normalization_2/moving_variance*
dtype0*
_output_shapes
:
j
%batch_normalization_2/batchnorm/add/yConst*
valueB
 *o�:*
dtype0*
_output_shapes
: 
�
#batch_normalization_2/batchnorm/addAdd.batch_normalization_2/batchnorm/ReadVariableOp%batch_normalization_2/batchnorm/add/y*
T0*
_output_shapes
:
x
%batch_normalization_2/batchnorm/RsqrtRsqrt#batch_normalization_2/batchnorm/add*
T0*
_output_shapes
:
�
2batch_normalization_2/batchnorm/mul/ReadVariableOpReadVariableOpbatch_normalization_2/gamma*
dtype0*
_output_shapes
:
�
#batch_normalization_2/batchnorm/mulMul%batch_normalization_2/batchnorm/Rsqrt2batch_normalization_2/batchnorm/mul/ReadVariableOp*
T0*
_output_shapes
:
�
%batch_normalization_2/batchnorm/mul_1MulDense_0/Relu#batch_normalization_2/batchnorm/mul*
T0*'
_output_shapes
:���������
�
0batch_normalization_2/batchnorm/ReadVariableOp_1ReadVariableOp!batch_normalization_2/moving_mean*
dtype0*
_output_shapes
:
�
%batch_normalization_2/batchnorm/mul_2Mul0batch_normalization_2/batchnorm/ReadVariableOp_1#batch_normalization_2/batchnorm/mul*
T0*
_output_shapes
:
�
0batch_normalization_2/batchnorm/ReadVariableOp_2ReadVariableOpbatch_normalization_2/beta*
dtype0*
_output_shapes
:
�
#batch_normalization_2/batchnorm/subSub0batch_normalization_2/batchnorm/ReadVariableOp_2%batch_normalization_2/batchnorm/mul_2*
T0*
_output_shapes
:
�
%batch_normalization_2/batchnorm/add_1Add%batch_normalization_2/batchnorm/mul_1#batch_normalization_2/batchnorm/sub*'
_output_shapes
:���������*
T0
�
.Output/kernel/Initializer/random_uniform/shapeConst*
dtype0*
_output_shapes
:*
valueB"      * 
_class
loc:@Output/kernel
�
,Output/kernel/Initializer/random_uniform/minConst*
valueB
 *0�* 
_class
loc:@Output/kernel*
dtype0*
_output_shapes
: 
�
,Output/kernel/Initializer/random_uniform/maxConst*
valueB
 *0?* 
_class
loc:@Output/kernel*
dtype0*
_output_shapes
: 
�
6Output/kernel/Initializer/random_uniform/RandomUniformRandomUniform.Output/kernel/Initializer/random_uniform/shape*
T0* 
_class
loc:@Output/kernel*
dtype0*
_output_shapes

:
�
,Output/kernel/Initializer/random_uniform/subSub,Output/kernel/Initializer/random_uniform/max,Output/kernel/Initializer/random_uniform/min*
T0* 
_class
loc:@Output/kernel*
_output_shapes
: 
�
,Output/kernel/Initializer/random_uniform/mulMul6Output/kernel/Initializer/random_uniform/RandomUniform,Output/kernel/Initializer/random_uniform/sub*
T0* 
_class
loc:@Output/kernel*
_output_shapes

:
�
(Output/kernel/Initializer/random_uniformAdd,Output/kernel/Initializer/random_uniform/mul,Output/kernel/Initializer/random_uniform/min*
T0* 
_class
loc:@Output/kernel*
_output_shapes

:
�
Output/kernelVarHandleOp*
shared_nameOutput/kernel* 
_class
loc:@Output/kernel*
shape
:*
dtype0*
_output_shapes
: 
k
.Output/kernel/IsInitialized/VarIsInitializedOpVarIsInitializedOpOutput/kernel*
_output_shapes
: 
�
Output/kernel/AssignAssignVariableOpOutput/kernel(Output/kernel/Initializer/random_uniform* 
_class
loc:@Output/kernel*
dtype0
�
!Output/kernel/Read/ReadVariableOpReadVariableOpOutput/kernel*
dtype0*
_output_shapes

:* 
_class
loc:@Output/kernel
�
Output/bias/Initializer/zerosConst*
valueB*    *
_class
loc:@Output/bias*
dtype0*
_output_shapes
:
�
Output/biasVarHandleOp*
_class
loc:@Output/bias*
shape:*
dtype0*
_output_shapes
: *
shared_nameOutput/bias
g
,Output/bias/IsInitialized/VarIsInitializedOpVarIsInitializedOpOutput/bias*
_output_shapes
: 

Output/bias/AssignAssignVariableOpOutput/biasOutput/bias/Initializer/zeros*
_class
loc:@Output/bias*
dtype0
�
Output/bias/Read/ReadVariableOpReadVariableOpOutput/bias*
_class
loc:@Output/bias*
dtype0*
_output_shapes
:
j
Output/MatMul/ReadVariableOpReadVariableOpOutput/kernel*
dtype0*
_output_shapes

:
�
Output/MatMulMatMul%batch_normalization_2/batchnorm/add_1Output/MatMul/ReadVariableOp*
T0*'
_output_shapes
:���������
e
Output/BiasAdd/ReadVariableOpReadVariableOpOutput/bias*
dtype0*
_output_shapes
:
y
Output/BiasAddBiasAddOutput/MatMulOutput/BiasAdd/ReadVariableOp*
T0*'
_output_shapes
:���������
[
Output/SigmoidSigmoidOutput/BiasAdd*
T0*'
_output_shapes
:���������

initNoOp

init_all_tablesNoOp

init_1NoOp
4

group_depsNoOp^init^init_1^init_all_tables
P

save/ConstConst*
valueB Bmodel*
dtype0*
_output_shapes
: 
�
save/StringJoin/inputs_1Const*<
value3B1 B+_temp_b802c0c2da4b4967985b5a7a80c82016/part*
dtype0*
_output_shapes
: 
d
save/StringJoin
StringJoin
save/Constsave/StringJoin/inputs_1*
N*
_output_shapes
: 
Q
save/num_shardsConst*
value	B :*
dtype0*
_output_shapes
: 
k
save/ShardedFilename/shardConst"/device:CPU:0*
dtype0*
_output_shapes
: *
value	B : 
�
save/ShardedFilenameShardedFilenamesave/StringJoinsave/ShardedFilename/shardsave/num_shards"/device:CPU:0*
_output_shapes
: 
�
save/SaveV2/tensor_namesConst"/device:CPU:0*
dtype0*
_output_shapes
:*�
value�B�BConv2D_0/biasBConv2D_0/kernelBConv2D_1/biasBConv2D_1/kernelBDense_0/biasBDense_0/kernelBOutput/biasBOutput/kernelBbatch_normalization/betaBbatch_normalization/gammaBbatch_normalization/moving_meanB#batch_normalization/moving_varianceBbatch_normalization_1/betaBbatch_normalization_1/gammaB!batch_normalization_1/moving_meanB%batch_normalization_1/moving_varianceBbatch_normalization_2/betaBbatch_normalization_2/gammaB!batch_normalization_2/moving_meanB%batch_normalization_2/moving_varianceBglobal_step
�
save/SaveV2/shape_and_slicesConst"/device:CPU:0*
dtype0*
_output_shapes
:*=
value4B2B B B B B B B B B B B B B B B B B B B B B 
�
save/SaveV2SaveV2save/ShardedFilenamesave/SaveV2/tensor_namessave/SaveV2/shape_and_slices!Conv2D_0/bias/Read/ReadVariableOp#Conv2D_0/kernel/Read/ReadVariableOp!Conv2D_1/bias/Read/ReadVariableOp#Conv2D_1/kernel/Read/ReadVariableOp Dense_0/bias/Read/ReadVariableOp"Dense_0/kernel/Read/ReadVariableOpOutput/bias/Read/ReadVariableOp!Output/kernel/Read/ReadVariableOp,batch_normalization/beta/Read/ReadVariableOp-batch_normalization/gamma/Read/ReadVariableOp3batch_normalization/moving_mean/Read/ReadVariableOp7batch_normalization/moving_variance/Read/ReadVariableOp.batch_normalization_1/beta/Read/ReadVariableOp/batch_normalization_1/gamma/Read/ReadVariableOp5batch_normalization_1/moving_mean/Read/ReadVariableOp9batch_normalization_1/moving_variance/Read/ReadVariableOp.batch_normalization_2/beta/Read/ReadVariableOp/batch_normalization_2/gamma/Read/ReadVariableOp5batch_normalization_2/moving_mean/Read/ReadVariableOp9batch_normalization_2/moving_variance/Read/ReadVariableOpglobal_step"/device:CPU:0*#
dtypes
2	
�
save/control_dependencyIdentitysave/ShardedFilename^save/SaveV2"/device:CPU:0*
T0*'
_class
loc:@save/ShardedFilename*
_output_shapes
: 
�
+save/MergeV2Checkpoints/checkpoint_prefixesPacksave/ShardedFilename^save/control_dependency"/device:CPU:0*
T0*
N*
_output_shapes
:
u
save/MergeV2CheckpointsMergeV2Checkpoints+save/MergeV2Checkpoints/checkpoint_prefixes
save/Const"/device:CPU:0
�
save/IdentityIdentity
save/Const^save/MergeV2Checkpoints^save/control_dependency"/device:CPU:0*
_output_shapes
: *
T0
�
save/RestoreV2/tensor_namesConst"/device:CPU:0*�
value�B�BConv2D_0/biasBConv2D_0/kernelBConv2D_1/biasBConv2D_1/kernelBDense_0/biasBDense_0/kernelBOutput/biasBOutput/kernelBbatch_normalization/betaBbatch_normalization/gammaBbatch_normalization/moving_meanB#batch_normalization/moving_varianceBbatch_normalization_1/betaBbatch_normalization_1/gammaB!batch_normalization_1/moving_meanB%batch_normalization_1/moving_varianceBbatch_normalization_2/betaBbatch_normalization_2/gammaB!batch_normalization_2/moving_meanB%batch_normalization_2/moving_varianceBglobal_step*
dtype0*
_output_shapes
:
�
save/RestoreV2/shape_and_slicesConst"/device:CPU:0*=
value4B2B B B B B B B B B B B B B B B B B B B B B *
dtype0*
_output_shapes
:
�
save/RestoreV2	RestoreV2
save/Constsave/RestoreV2/tensor_namessave/RestoreV2/shape_and_slices"/device:CPU:0*h
_output_shapesV
T:::::::::::::::::::::*#
dtypes
2	
N
save/Identity_1Identitysave/RestoreV2*
T0*
_output_shapes
:
V
save/AssignVariableOpAssignVariableOpConv2D_0/biassave/Identity_1*
dtype0
P
save/Identity_2Identitysave/RestoreV2:1*
_output_shapes
:*
T0
Z
save/AssignVariableOp_1AssignVariableOpConv2D_0/kernelsave/Identity_2*
dtype0
P
save/Identity_3Identitysave/RestoreV2:2*
_output_shapes
:*
T0
X
save/AssignVariableOp_2AssignVariableOpConv2D_1/biassave/Identity_3*
dtype0
P
save/Identity_4Identitysave/RestoreV2:3*
T0*
_output_shapes
:
Z
save/AssignVariableOp_3AssignVariableOpConv2D_1/kernelsave/Identity_4*
dtype0
P
save/Identity_5Identitysave/RestoreV2:4*
T0*
_output_shapes
:
W
save/AssignVariableOp_4AssignVariableOpDense_0/biassave/Identity_5*
dtype0
P
save/Identity_6Identitysave/RestoreV2:5*
_output_shapes
:*
T0
Y
save/AssignVariableOp_5AssignVariableOpDense_0/kernelsave/Identity_6*
dtype0
P
save/Identity_7Identitysave/RestoreV2:6*
T0*
_output_shapes
:
V
save/AssignVariableOp_6AssignVariableOpOutput/biassave/Identity_7*
dtype0
P
save/Identity_8Identitysave/RestoreV2:7*
T0*
_output_shapes
:
X
save/AssignVariableOp_7AssignVariableOpOutput/kernelsave/Identity_8*
dtype0
P
save/Identity_9Identitysave/RestoreV2:8*
_output_shapes
:*
T0
c
save/AssignVariableOp_8AssignVariableOpbatch_normalization/betasave/Identity_9*
dtype0
Q
save/Identity_10Identitysave/RestoreV2:9*
_output_shapes
:*
T0
e
save/AssignVariableOp_9AssignVariableOpbatch_normalization/gammasave/Identity_10*
dtype0
R
save/Identity_11Identitysave/RestoreV2:10*
T0*
_output_shapes
:
l
save/AssignVariableOp_10AssignVariableOpbatch_normalization/moving_meansave/Identity_11*
dtype0
R
save/Identity_12Identitysave/RestoreV2:11*
_output_shapes
:*
T0
p
save/AssignVariableOp_11AssignVariableOp#batch_normalization/moving_variancesave/Identity_12*
dtype0
R
save/Identity_13Identitysave/RestoreV2:12*
T0*
_output_shapes
:
g
save/AssignVariableOp_12AssignVariableOpbatch_normalization_1/betasave/Identity_13*
dtype0
R
save/Identity_14Identitysave/RestoreV2:13*
_output_shapes
:*
T0
h
save/AssignVariableOp_13AssignVariableOpbatch_normalization_1/gammasave/Identity_14*
dtype0
R
save/Identity_15Identitysave/RestoreV2:14*
T0*
_output_shapes
:
n
save/AssignVariableOp_14AssignVariableOp!batch_normalization_1/moving_meansave/Identity_15*
dtype0
R
save/Identity_16Identitysave/RestoreV2:15*
_output_shapes
:*
T0
r
save/AssignVariableOp_15AssignVariableOp%batch_normalization_1/moving_variancesave/Identity_16*
dtype0
R
save/Identity_17Identitysave/RestoreV2:16*
_output_shapes
:*
T0
g
save/AssignVariableOp_16AssignVariableOpbatch_normalization_2/betasave/Identity_17*
dtype0
R
save/Identity_18Identitysave/RestoreV2:17*
T0*
_output_shapes
:
h
save/AssignVariableOp_17AssignVariableOpbatch_normalization_2/gammasave/Identity_18*
dtype0
R
save/Identity_19Identitysave/RestoreV2:18*
T0*
_output_shapes
:
n
save/AssignVariableOp_18AssignVariableOp!batch_normalization_2/moving_meansave/Identity_19*
dtype0
R
save/Identity_20Identitysave/RestoreV2:19*
T0*
_output_shapes
:
r
save/AssignVariableOp_19AssignVariableOp%batch_normalization_2/moving_variancesave/Identity_20*
dtype0
v
save/AssignAssignglobal_stepsave/RestoreV2:20*
T0	*
_class
loc:@global_step*
_output_shapes
: 
�
save/restore_shardNoOp^save/Assign^save/AssignVariableOp^save/AssignVariableOp_1^save/AssignVariableOp_10^save/AssignVariableOp_11^save/AssignVariableOp_12^save/AssignVariableOp_13^save/AssignVariableOp_14^save/AssignVariableOp_15^save/AssignVariableOp_16^save/AssignVariableOp_17^save/AssignVariableOp_18^save/AssignVariableOp_19^save/AssignVariableOp_2^save/AssignVariableOp_3^save/AssignVariableOp_4^save/AssignVariableOp_5^save/AssignVariableOp_6^save/AssignVariableOp_7^save/AssignVariableOp_8^save/AssignVariableOp_9
-
save/restore_allNoOp^save/restore_shard"<
save/Const:0save/Identity:0save/restore_all (5 @F8"�
trainable_variables��
�
Conv2D_0/kernel:0Conv2D_0/kernel/Assign%Conv2D_0/kernel/Read/ReadVariableOp:0(2,Conv2D_0/kernel/Initializer/random_uniform:08
s
Conv2D_0/bias:0Conv2D_0/bias/Assign#Conv2D_0/bias/Read/ReadVariableOp:0(2!Conv2D_0/bias/Initializer/zeros:08
�
batch_normalization/gamma:0 batch_normalization/gamma/Assign/batch_normalization/gamma/Read/ReadVariableOp:0(2,batch_normalization/gamma/Initializer/ones:08
�
batch_normalization/beta:0batch_normalization/beta/Assign.batch_normalization/beta/Read/ReadVariableOp:0(2,batch_normalization/beta/Initializer/zeros:08
�
Conv2D_1/kernel:0Conv2D_1/kernel/Assign%Conv2D_1/kernel/Read/ReadVariableOp:0(2,Conv2D_1/kernel/Initializer/random_uniform:08
s
Conv2D_1/bias:0Conv2D_1/bias/Assign#Conv2D_1/bias/Read/ReadVariableOp:0(2!Conv2D_1/bias/Initializer/zeros:08
�
batch_normalization_1/gamma:0"batch_normalization_1/gamma/Assign1batch_normalization_1/gamma/Read/ReadVariableOp:0(2.batch_normalization_1/gamma/Initializer/ones:08
�
batch_normalization_1/beta:0!batch_normalization_1/beta/Assign0batch_normalization_1/beta/Read/ReadVariableOp:0(2.batch_normalization_1/beta/Initializer/zeros:08
�
Dense_0/kernel:0Dense_0/kernel/Assign$Dense_0/kernel/Read/ReadVariableOp:0(2+Dense_0/kernel/Initializer/random_uniform:08
o
Dense_0/bias:0Dense_0/bias/Assign"Dense_0/bias/Read/ReadVariableOp:0(2 Dense_0/bias/Initializer/zeros:08
�
batch_normalization_2/gamma:0"batch_normalization_2/gamma/Assign1batch_normalization_2/gamma/Read/ReadVariableOp:0(2.batch_normalization_2/gamma/Initializer/ones:08
�
batch_normalization_2/beta:0!batch_normalization_2/beta/Assign0batch_normalization_2/beta/Read/ReadVariableOp:0(2.batch_normalization_2/beta/Initializer/zeros:08
|
Output/kernel:0Output/kernel/Assign#Output/kernel/Read/ReadVariableOp:0(2*Output/kernel/Initializer/random_uniform:08
k
Output/bias:0Output/bias/Assign!Output/bias/Read/ReadVariableOp:0(2Output/bias/Initializer/zeros:08"k
global_step\Z
X
global_step:0global_step/Assignglobal_step/read:02global_step/Initializer/zeros:0"%
saved_model_main_op


group_deps"�
	variables��
X
global_step:0global_step/Assignglobal_step/read:02global_step/Initializer/zeros:0
�
Conv2D_0/kernel:0Conv2D_0/kernel/Assign%Conv2D_0/kernel/Read/ReadVariableOp:0(2,Conv2D_0/kernel/Initializer/random_uniform:08
s
Conv2D_0/bias:0Conv2D_0/bias/Assign#Conv2D_0/bias/Read/ReadVariableOp:0(2!Conv2D_0/bias/Initializer/zeros:08
�
batch_normalization/gamma:0 batch_normalization/gamma/Assign/batch_normalization/gamma/Read/ReadVariableOp:0(2,batch_normalization/gamma/Initializer/ones:08
�
batch_normalization/beta:0batch_normalization/beta/Assign.batch_normalization/beta/Read/ReadVariableOp:0(2,batch_normalization/beta/Initializer/zeros:08
�
!batch_normalization/moving_mean:0&batch_normalization/moving_mean/Assign5batch_normalization/moving_mean/Read/ReadVariableOp:0(23batch_normalization/moving_mean/Initializer/zeros:0
�
%batch_normalization/moving_variance:0*batch_normalization/moving_variance/Assign9batch_normalization/moving_variance/Read/ReadVariableOp:0(26batch_normalization/moving_variance/Initializer/ones:0
�
Conv2D_1/kernel:0Conv2D_1/kernel/Assign%Conv2D_1/kernel/Read/ReadVariableOp:0(2,Conv2D_1/kernel/Initializer/random_uniform:08
s
Conv2D_1/bias:0Conv2D_1/bias/Assign#Conv2D_1/bias/Read/ReadVariableOp:0(2!Conv2D_1/bias/Initializer/zeros:08
�
batch_normalization_1/gamma:0"batch_normalization_1/gamma/Assign1batch_normalization_1/gamma/Read/ReadVariableOp:0(2.batch_normalization_1/gamma/Initializer/ones:08
�
batch_normalization_1/beta:0!batch_normalization_1/beta/Assign0batch_normalization_1/beta/Read/ReadVariableOp:0(2.batch_normalization_1/beta/Initializer/zeros:08
�
#batch_normalization_1/moving_mean:0(batch_normalization_1/moving_mean/Assign7batch_normalization_1/moving_mean/Read/ReadVariableOp:0(25batch_normalization_1/moving_mean/Initializer/zeros:0
�
'batch_normalization_1/moving_variance:0,batch_normalization_1/moving_variance/Assign;batch_normalization_1/moving_variance/Read/ReadVariableOp:0(28batch_normalization_1/moving_variance/Initializer/ones:0
�
Dense_0/kernel:0Dense_0/kernel/Assign$Dense_0/kernel/Read/ReadVariableOp:0(2+Dense_0/kernel/Initializer/random_uniform:08
o
Dense_0/bias:0Dense_0/bias/Assign"Dense_0/bias/Read/ReadVariableOp:0(2 Dense_0/bias/Initializer/zeros:08
�
batch_normalization_2/gamma:0"batch_normalization_2/gamma/Assign1batch_normalization_2/gamma/Read/ReadVariableOp:0(2.batch_normalization_2/gamma/Initializer/ones:08
�
batch_normalization_2/beta:0!batch_normalization_2/beta/Assign0batch_normalization_2/beta/Read/ReadVariableOp:0(2.batch_normalization_2/beta/Initializer/zeros:08
�
#batch_normalization_2/moving_mean:0(batch_normalization_2/moving_mean/Assign7batch_normalization_2/moving_mean/Read/ReadVariableOp:0(25batch_normalization_2/moving_mean/Initializer/zeros:0
�
'batch_normalization_2/moving_variance:0,batch_normalization_2/moving_variance/Assign;batch_normalization_2/moving_variance/Read/ReadVariableOp:0(28batch_normalization_2/moving_variance/Initializer/ones:0
|
Output/kernel:0Output/kernel/Assign#Output/kernel/Read/ReadVariableOp:0(2*Output/kernel/Initializer/random_uniform:08
k
Output/bias:0Output/bias/Assign!Output/bias/Read/ReadVariableOp:0(2Output/bias/Initializer/zeros:08*�
serving_default�
>
Conv2D_0_input,
Placeholder:0���������K!1
Output'
Output/Sigmoid:0���������tensorflow/serving/predict